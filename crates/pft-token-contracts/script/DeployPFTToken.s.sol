// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {PFTToken} from "../src/PFTToken.sol";

interface IPFTTokenDeployVm {
    function envString(string calldata name) external view returns (string memory);
    function envOr(string calldata name, string calldata defaultValue) external view returns (string memory);
    function parseUint(string calldata value) external pure returns (uint256);
    function parseAddress(string calldata value) external pure returns (address);
    function getNonce(address account) external view returns (uint64);
    function load(address target, bytes32 slot) external view returns (bytes32 data);
    function exists(string calldata path) external view returns (bool);
    function isContext(uint8 context) external view returns (bool);
    function startBroadcast(address signer) external;
    function stopBroadcast() external;
    function toString(uint256 value) external pure returns (string memory);
    function toString(bytes calldata value) external pure returns (string memory);
    function readFile(string calldata path) external view returns (string memory);
    function parseTomlString(string calldata toml, string calldata key) external pure returns (string memory);
    function parseTomlUint(string calldata toml, string calldata key) external pure returns (uint256);
    function parseTomlBool(string calldata toml, string calldata key) external pure returns (bool);
    function serializeString(string calldata objectKey, string calldata valueKey, string calldata value)
        external
        returns (string memory);
    function serializeAddress(string calldata objectKey, string calldata valueKey, address value)
        external
        returns (string memory);
    function serializeUint(string calldata objectKey, string calldata valueKey, uint256 value)
        external
        returns (string memory);
    function serializeBool(string calldata objectKey, string calldata valueKey, bool value)
        external
        returns (string memory);
    function serializeAddress(string calldata objectKey, string calldata valueKey, address[] calldata values)
        external
        returns (string memory);
    function createDir(string calldata path, bool recursive) external;
    function writeFile(string calldata path, string calldata data) external;
}

/// The read-only part of the Safe interface the probe calls with checked staticcalls.
interface ISafeProbe {
    function getThreshold() external view returns (uint256);
    function getOwners() external view returns (address[] memory);
}

/// @notice Foundry deployment script for the fixed-supply PFT token on Base.
/// @dev No forge-std dependency is required; the script declares only the
///      cheatcodes it uses. The values come from the environment (see
///      `script/pft-token.env.example`); the RPC URL and the one-time deployer
///      key are given to `forge script` on the command line and are never read
///      from a file by this script. Every check runs before the broadcast.
contract DeployPFTToken {
    IPFTTokenDeployVm private constant VM = IPFTTokenDeployVm(address(uint160(uint256(keccak256("hevm cheat code")))));
    address private constant CONSOLE = 0x000000000000000000636F6e736F6c652e6c6f67;

    uint256 public constant BASE = 8453;
    uint256 public constant BASE_SEPOLIA = 84532;
    uint256 public constant UNITS_PER_PFT = 1_000_000;
    /// OpenZeppelin v5.7.0 EIP712 stores the name as a ShortString (at most 31 bytes).
    uint256 public constant MAX_NAME_BYTES = 31;
    string public constant OPENZEPPELIN_COMMIT = "cab19933c33c2ad1d4c7a84864a3601dddfd16f3";
    /// `ForgeContext.ScriptBroadcast` in forge-std's Vm.
    uint8 private constant SCRIPT_BROADCAST = 6;

    /// Official Safe singletons, the address a Safe proxy keeps in storage slot 0.
    /// Source: safe-global/safe-deployments (commit b45417dd009957effb3575928941e736f8fd37d1),
    /// src/assets/v1.4.1/safe.json, safe_l2.json and src/assets/v1.3.0/gnosis_safe.json,
    /// gnosis_safe_l2.json: the "canonical" deployment, listed there for 8453 and 84532.
    /// The v1.3.0 "eip155" deployment is listed for both chains too and is not pinned.
    address public constant SAFE_1_4_1 = 0x41675C099F32341bf84BFc5382aF534df5C7461a;
    address public constant SAFE_L2_1_4_1 = 0x29fcB43b46531BcA003ddC8FCB67FFE91900C762;
    address public constant SAFE_1_3_0 = 0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552;
    address public constant SAFE_L2_1_3_0 = 0x3E5c63644E683549055b9Be8653de26E0B4CD36E;
    uint256 public constant MIN_SAFE_THRESHOLD = 2;

    struct Config {
        uint256 chainId;
        string name;
        string symbol;
        uint256 totalSupply; // six-decimal units
        uint256 totalSupplyPft; // whole PFT
        address treasury;
        bool allowEoaTreasury; // Base Sepolia dry run only
        bool allowUsedDeployer; // Base Sepolia dry run only
        bool realDeployment; // PFT_TOKEN_REAL_DEPLOYMENT=1: the durable record under deployments/
        string recordDir; // deployments/... for a real deployment, else cache/deploy-test/...
        bool writeRecord; // only `forge script --broadcast` writes the record
        string sourceCommit; // PFT_TOKEN_SOURCE_COMMIT, may be empty
    }

    struct SafeInfo {
        address singleton;
        uint256 threshold;
        address[] owners;
    }

    error PlaceholderValue(string name);
    error UnsupportedChain(uint256 chainId);
    error WrongChain(uint256 expected, uint256 actual);
    error TestSwitchOnMainnet(string name);
    error NameTooLong(uint256 length);
    error SupplyMismatch(uint256 units, uint256 pft);
    error TreasuryIsDeployer(address treasury);
    error TreasuryNotAContract(address treasury);
    error TreasuryIsNotASafe(address treasury);
    error UnofficialSafeSingleton(address treasury, address singleton);
    error SafeThresholdTooLow(uint256 threshold);
    error SafeOwnersInvalid(uint256 owners, uint256 distinctNonZero, uint256 threshold);
    error DeployerAlreadyUsed(address deployer, uint256 nonce);
    error RealDeploymentWithTestSwitch(string name);
    error RecordExists(string path);

    event PFTTokenDeployed(
        address indexed token, address indexed treasury, uint256 total_supply, string name, string symbol
    );

    function run() external returns (PFTToken) {
        return deploy(readConfig());
    }

    /// Reads the deployment values from the environment. The record is written
    /// only by `forge script --broadcast`, never by a dry run. Only
    /// PFT_TOKEN_REAL_DEPLOYMENT=1 selects the durable deployments/ path; every
    /// other run writes under the ignored cache/deploy-test/.
    function readConfig() public view returns (Config memory cfg) {
        cfg.chainId = VM.parseUint(_required("PFT_TOKEN_CHAIN_ID"));
        cfg.name = _required("PFT_TOKEN_NAME");
        cfg.symbol = _required("PFT_TOKEN_SYMBOL");
        cfg.totalSupply = VM.parseUint(_required("PFT_TOKEN_TOTAL_SUPPLY"));
        cfg.totalSupplyPft = VM.parseUint(_required("PFT_TOKEN_TOTAL_SUPPLY_PFT"));
        cfg.treasury = VM.parseAddress(_required("PFT_TOKEN_TREASURY"));
        cfg.allowEoaTreasury = _switch("PFT_TOKEN_ALLOW_EOA_TREASURY");
        cfg.allowUsedDeployer = _switch("PFT_TOKEN_ALLOW_USED_DEPLOYER");
        cfg.realDeployment = _switch("PFT_TOKEN_REAL_DEPLOYMENT");
        string memory root = cfg.realDeployment ? "deployments/" : "cache/deploy-test/";
        cfg.recordDir = string.concat(root, "pft-token-base-", VM.toString(block.chainid));
        cfg.writeRecord = VM.isContext(SCRIPT_BROADCAST);
        cfg.sourceCommit = VM.envOr("PFT_TOKEN_SOURCE_COMMIT", string(""));
    }

    /// Checks `cfg` against the target chain, then deploys from `msg.sender`
    /// (the broadcaster) and writes the record.
    function deploy(Config memory cfg) public returns (PFTToken token) {
        address deployer = msg.sender;
        _checkChain(cfg);
        _checkMetadata(cfg);
        _checkSupply(cfg);
        SafeInfo memory safe = _checkTreasury(cfg, deployer);
        uint256 nonce = VM.getNonce(deployer);
        if (nonce != 0 && !cfg.allowUsedDeployer) {
            revert DeployerAlreadyUsed(deployer, nonce);
        }
        string memory recordPath = string.concat(cfg.recordDir, "/deployment.json");
        if (cfg.realDeployment && VM.exists(recordPath)) revert RecordExists(recordPath);

        _log("chain id", block.chainid);
        _log("name", cfg.name);
        _log("symbol", cfg.symbol);
        _log("deployer", deployer);
        _log("deployer nonce", nonce);
        _log("treasury", cfg.treasury);
        _log("treasury Safe singleton", safe.singleton);
        _log("treasury Safe threshold", safe.threshold);
        _log("treasury Safe owners", safe.owners.length);
        _log("deployment record", cfg.realDeployment ? "real" : "test");
        _log("total supply (six-decimal units)", cfg.totalSupply);
        _log("total supply (whole PFT)", cfg.totalSupplyPft);

        VM.startBroadcast(deployer);
        token = new PFTToken(cfg.name, cfg.symbol, cfg.totalSupply, cfg.treasury);
        VM.stopBroadcast();

        emit PFTTokenDeployed(address(token), cfg.treasury, cfg.totalSupply, cfg.name, cfg.symbol);
        _log("PFTToken deployed at", address(token));
        if (cfg.writeRecord) {
            _writeRecord(cfg, token, deployer, safe, recordPath);
        }
    }

    /// True for a pinned official Safe singleton on 8453 or 84532.
    function isOfficialSafeSingleton(uint256 chainId, address singleton) public pure returns (bool) {
        if (chainId != BASE && chainId != BASE_SEPOLIA) return false;
        return
            singleton == SAFE_1_4_1 || singleton == SAFE_L2_1_4_1 || singleton == SAFE_1_3_0
                || singleton == SAFE_L2_1_3_0;
    }

    /// Fails closed unless `treasury` is a proxy of a pinned official Safe
    /// singleton with threshold >= 2 and at least that many distinct non-zero
    /// owners. Reads slot 0 and probes with checked staticcalls (no self-call).
    function checkSafe(uint256 chainId, address treasury) public view returns (SafeInfo memory safe) {
        bytes32 slot0 = VM.load(treasury, bytes32(0));
        safe.singleton = address(uint160(uint256(slot0)));
        if (uint256(slot0) >> 160 != 0 || !isOfficialSafeSingleton(chainId, safe.singleton)) {
            revert UnofficialSafeSingleton(treasury, safe.singleton);
        }
        (bool ok, bytes memory ret) = treasury.staticcall(abi.encodeCall(ISafeProbe.getThreshold, ()));
        if (!ok || ret.length != 32) revert TreasuryIsNotASafe(treasury);
        safe.threshold = abi.decode(ret, (uint256));
        (ok, ret) = treasury.staticcall(abi.encodeCall(ISafeProbe.getOwners, ()));
        if (!ok || ret.length < 64) revert TreasuryIsNotASafe(treasury);
        (uint256 offset, uint256 count) = abi.decode(ret, (uint256, uint256));
        if (offset != 32 || count > (ret.length - 64) / 32 || ret.length != 64 + count * 32) {
            revert TreasuryIsNotASafe(treasury);
        }
        safe.owners = abi.decode(ret, (address[]));
        if (safe.threshold < MIN_SAFE_THRESHOLD) revert SafeThresholdTooLow(safe.threshold);
        uint256 distinct = _distinctNonZero(safe.owners);
        if (distinct != count || distinct < MIN_SAFE_THRESHOLD || safe.threshold > distinct) {
            revert SafeOwnersInvalid(count, distinct, safe.threshold);
        }
    }

    function _checkChain(Config memory cfg) private view {
        if (cfg.chainId != BASE && cfg.chainId != BASE_SEPOLIA) {
            revert UnsupportedChain(cfg.chainId);
        }
        if (cfg.chainId != block.chainid) {
            revert WrongChain(cfg.chainId, block.chainid);
        }
        if (cfg.chainId == BASE) {
            if (cfg.allowEoaTreasury) revert TestSwitchOnMainnet("PFT_TOKEN_ALLOW_EOA_TREASURY");
            if (cfg.allowUsedDeployer) revert TestSwitchOnMainnet("PFT_TOKEN_ALLOW_USED_DEPLOYER");
        }
        if (cfg.realDeployment) {
            if (cfg.allowEoaTreasury) revert RealDeploymentWithTestSwitch("PFT_TOKEN_ALLOW_EOA_TREASURY");
            if (cfg.allowUsedDeployer) revert RealDeploymentWithTestSwitch("PFT_TOKEN_ALLOW_USED_DEPLOYER");
        }
    }

    function _checkMetadata(Config memory cfg) private pure {
        if (_isPlaceholder(bytes(cfg.name))) revert PlaceholderValue("PFT_TOKEN_NAME");
        if (_isPlaceholder(bytes(cfg.symbol))) revert PlaceholderValue("PFT_TOKEN_SYMBOL");
        if (bytes(cfg.name).length > MAX_NAME_BYTES) revert NameTooLong(bytes(cfg.name).length);
    }

    function _checkSupply(Config memory cfg) private pure {
        if (cfg.totalSupply == 0) revert PlaceholderValue("PFT_TOKEN_TOTAL_SUPPLY");
        if (
            cfg.totalSupplyPft > type(uint256).max / UNITS_PER_PFT
                || cfg.totalSupply != cfg.totalSupplyPft * UNITS_PER_PFT
        ) {
            revert SupplyMismatch(cfg.totalSupply, cfg.totalSupplyPft);
        }
    }

    /// The only relaxation: the test switch admits a treasury without code on
    /// 84532 (refused on 8453 by _checkChain). A contract must pass checkSafe.
    function _checkTreasury(Config memory cfg, address deployer) private view returns (SafeInfo memory safe) {
        if (cfg.treasury == address(0)) revert PlaceholderValue("PFT_TOKEN_TREASURY");
        if (cfg.treasury == deployer) revert TreasuryIsDeployer(cfg.treasury);
        if (cfg.treasury.code.length == 0) {
            if (!cfg.allowEoaTreasury) revert TreasuryNotAContract(cfg.treasury);
            _log("WARNING: test-only PFT_TOKEN_ALLOW_EOA_TREASURY; the treasury has no code");
            return safe;
        }
        return checkSafe(cfg.chainId, cfg.treasury);
    }

    function _distinctNonZero(address[] memory owners) private pure returns (uint256 distinct) {
        for (uint256 i = 0; i < owners.length; i++) {
            bool repeated = owners[i] == address(0);
            for (uint256 j = 0; j < i && !repeated; j++) {
                repeated = owners[j] == owners[i];
            }
            if (!repeated) distinct++;
        }
    }

    /// The broadcast transaction hash and block are not known while the script
    /// runs; they are "pending" here and copied in from broadcast/.../run-latest.json.
    function _writeRecord(Config memory cfg, PFTToken token, address deployer, SafeInfo memory safe, string memory path)
        private
    {
        string memory o = "pft_token_deployment";
        string memory toml = VM.readFile("foundry.toml");
        VM.serializeString(o, "mode", cfg.realDeployment ? "real" : "test");
        VM.serializeString(o, "tx_hash", "pending");
        VM.serializeString(o, "block_number", "pending");
        VM.serializeAddress(o, "token", address(token));
        VM.serializeUint(o, "chain_id", block.chainid);
        VM.serializeString(o, "name", cfg.name);
        VM.serializeString(o, "symbol", cfg.symbol);
        VM.serializeString(o, "total_supply_units", VM.toString(cfg.totalSupply));
        VM.serializeString(o, "total_supply_pft", VM.toString(cfg.totalSupplyPft));
        VM.serializeAddress(o, "treasury", cfg.treasury);
        VM.serializeString(
            o, "constructor_args", VM.toString(abi.encode(cfg.name, cfg.symbol, cfg.totalSupply, cfg.treasury))
        );
        VM.serializeAddress(o, "deployer", deployer);
        VM.serializeAddress(o, "treasury_safe_singleton", safe.singleton);
        VM.serializeUint(o, "treasury_safe_threshold", safe.threshold);
        VM.serializeUint(o, "treasury_safe_owner_count", safe.owners.length);
        VM.serializeAddress(o, "treasury_safe_owners", safe.owners);
        VM.serializeString(o, "solc_version", VM.parseTomlString(toml, ".profile.default.solc_version"));
        VM.serializeBool(o, "optimizer", VM.parseTomlBool(toml, ".profile.default.optimizer"));
        VM.serializeUint(o, "optimizer_runs", VM.parseTomlUint(toml, ".profile.default.optimizer_runs"));
        VM.serializeString(o, "evm_version", VM.parseTomlString(toml, ".profile.default.evm_version"));
        VM.serializeString(o, "bytecode_hash", VM.parseTomlString(toml, ".profile.default.bytecode_hash"));
        VM.serializeBool(o, "cbor_metadata", VM.parseTomlBool(toml, ".profile.default.cbor_metadata"));
        VM.serializeString(o, "source_commit", cfg.sourceCommit);
        string memory json = VM.serializeString(o, "openzeppelin_commit", OPENZEPPELIN_COMMIT);
        VM.createDir(cfg.recordDir, true);
        VM.writeFile(path, json);
        _log(string.concat("deployment record written to ", path));
    }

    /// Refuses an unset, empty, whitespace-only or `replace...` (any casing) value.
    function _required(string memory name) private view returns (string memory value) {
        value = VM.envString(name);
        if (_isPlaceholder(bytes(value))) revert PlaceholderValue(name);
    }

    /// A test-only switch is on only when set to exactly "1".
    function _switch(string memory name) private view returns (bool) {
        return keccak256(bytes(VM.envOr(name, string("")))) == keccak256("1");
    }

    function _isPlaceholder(bytes memory value) private pure returns (bool) {
        bool blank = true;
        bytes memory lower = new bytes(value.length);
        for (uint256 i = 0; i < value.length; i++) {
            bytes1 c = value[i];
            if (c >= "A" && c <= "Z") c = bytes1(uint8(c) + 32);
            lower[i] = c;
            if (c != " " && (c < 0x09 || c > 0x0d)) blank = false;
        }
        return blank || _contains(lower, bytes("replace"));
    }

    function _contains(bytes memory haystack, bytes memory needle) private pure returns (bool) {
        if (needle.length > haystack.length) {
            return false;
        }
        for (uint256 i = 0; i <= haystack.length - needle.length; i++) {
            uint256 j = 0;
            while (j < needle.length && haystack[i + j] == needle[j]) {
                j++;
            }
            if (j == needle.length) {
                return true;
            }
        }
        return false;
    }

    function _log(string memory label) private view {
        (bool ok,) = CONSOLE.staticcall(abi.encodeWithSignature("log(string)", label));
        ok;
    }

    function _log(string memory label, address value) private view {
        (bool ok,) = CONSOLE.staticcall(abi.encodeWithSignature("log(string,address)", label, value));
        ok;
    }

    function _log(string memory label, string memory value) private view {
        (bool ok,) = CONSOLE.staticcall(abi.encodeWithSignature("log(string,string)", label, value));
        ok;
    }

    function _log(string memory label, uint256 value) private view {
        (bool ok,) = CONSOLE.staticcall(abi.encodeWithSignature("log(string,uint256)", label, value));
        ok;
    }
}
