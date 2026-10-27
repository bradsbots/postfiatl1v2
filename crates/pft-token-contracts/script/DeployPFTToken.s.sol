// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {PFTToken} from "../src/PFTToken.sol";

interface IPFTTokenDeployVm {
    function envString(string calldata name) external view returns (string memory);
    function envOr(string calldata name, string calldata defaultValue) external view returns (string memory);
    function parseUint(string calldata value) external pure returns (uint256);
    function parseAddress(string calldata value) external pure returns (address);
    function getNonce(address account) external view returns (uint64);
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
    function createDir(string calldata path, bool recursive) external;
    function writeFile(string calldata path, string calldata data) external;
}

/// The read-only part of the Safe interface the probe calls.
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

    struct Config {
        uint256 chainId;
        string name;
        string symbol;
        uint256 totalSupply; // six-decimal units
        uint256 totalSupplyPft; // whole PFT
        address treasury;
        bool allowEoaTreasury; // Base Sepolia dry run only
        bool allowUsedDeployer; // Base Sepolia dry run only
        string recordDir; // empty: write no deployment record
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
    error DeployerAlreadyUsed(address deployer, uint256 nonce);

    event PFTTokenDeployed(
        address indexed token, address indexed treasury, uint256 total_supply, string name, string symbol
    );

    function run() external returns (PFTToken) {
        return deploy(readConfig());
    }

    /// Reads the deployment values from the environment. The record is written
    /// only by `forge script --broadcast`, never by a dry run.
    function readConfig() public view returns (Config memory cfg) {
        cfg.chainId = VM.parseUint(_required("PFT_TOKEN_CHAIN_ID"));
        cfg.name = _required("PFT_TOKEN_NAME");
        cfg.symbol = _required("PFT_TOKEN_SYMBOL");
        cfg.totalSupply = VM.parseUint(_required("PFT_TOKEN_TOTAL_SUPPLY"));
        cfg.totalSupplyPft = VM.parseUint(_required("PFT_TOKEN_TOTAL_SUPPLY_PFT"));
        cfg.treasury = VM.parseAddress(_required("PFT_TOKEN_TREASURY"));
        cfg.allowEoaTreasury = _switch("PFT_TOKEN_ALLOW_EOA_TREASURY");
        cfg.allowUsedDeployer = _switch("PFT_TOKEN_ALLOW_USED_DEPLOYER");
        if (VM.isContext(SCRIPT_BROADCAST)) {
            cfg.recordDir = string.concat("deployments/pft-token-base-", VM.toString(block.chainid));
        }
    }

    /// Checks `cfg` against the target chain, then deploys from `msg.sender`
    /// (the broadcaster) and writes the record.
    function deploy(Config memory cfg) public returns (PFTToken token) {
        address deployer = msg.sender;
        _checkChain(cfg);
        _checkMetadata(cfg);
        _checkSupply(cfg);
        (uint256 threshold, uint256 owners) = _checkTreasury(cfg, deployer);
        uint256 nonce = VM.getNonce(deployer);
        if (nonce != 0 && !cfg.allowUsedDeployer) {
            revert DeployerAlreadyUsed(deployer, nonce);
        }

        _log("chain id", block.chainid);
        _log("name", cfg.name);
        _log("symbol", cfg.symbol);
        _log("deployer", deployer);
        _log("deployer nonce", nonce);
        _log("treasury", cfg.treasury);
        _log("treasury Safe threshold", threshold);
        _log("treasury Safe owners", owners);
        _log("total supply (six-decimal units)", cfg.totalSupply);
        _log("total supply (whole PFT)", cfg.totalSupplyPft);

        VM.startBroadcast(deployer);
        token = new PFTToken(cfg.name, cfg.symbol, cfg.totalSupply, cfg.treasury);
        VM.stopBroadcast();

        emit PFTTokenDeployed(address(token), cfg.treasury, cfg.totalSupply, cfg.name, cfg.symbol);
        _log("PFTToken deployed at", address(token));
        if (bytes(cfg.recordDir).length != 0) {
            _writeRecord(cfg, token, deployer, threshold, owners);
        }
    }

    /// Read-only Safe probe; reverts unless the answers fit a Safe (1 <= threshold <= owners).
    function probeSafe(address treasury) external view returns (uint256 threshold, uint256 owners) {
        threshold = ISafeProbe(treasury).getThreshold();
        owners = ISafeProbe(treasury).getOwners().length;
        if (threshold == 0 || threshold > owners) {
            revert TreasuryIsNotASafe(treasury);
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
    }

    function _checkMetadata(Config memory cfg) private pure {
        if (_isPlaceholder(bytes(cfg.name))) revert PlaceholderValue("PFT_TOKEN_NAME");
        if (_isPlaceholder(bytes(cfg.symbol))) revert PlaceholderValue("PFT_TOKEN_SYMBOL");
        if (bytes(cfg.name).length > MAX_NAME_BYTES) revert NameTooLong(bytes(cfg.name).length);
    }

    function _checkSupply(Config memory cfg) private pure {
        if (cfg.totalSupply == 0) revert PlaceholderValue("PFT_TOKEN_TOTAL_SUPPLY");
        if (cfg.totalSupplyPft > type(uint256).max / UNITS_PER_PFT || cfg.totalSupply != cfg.totalSupplyPft * UNITS_PER_PFT)
        {
            revert SupplyMismatch(cfg.totalSupply, cfg.totalSupplyPft);
        }
    }

    function _checkTreasury(Config memory cfg, address deployer) private view returns (uint256 threshold, uint256 owners) {
        if (cfg.treasury == address(0)) revert PlaceholderValue("PFT_TOKEN_TREASURY");
        if (cfg.treasury == deployer) revert TreasuryIsDeployer(cfg.treasury);
        if (cfg.treasury.code.length == 0) {
            if (!cfg.allowEoaTreasury) revert TreasuryNotAContract(cfg.treasury);
            _log("WARNING: test-only PFT_TOKEN_ALLOW_EOA_TREASURY; the treasury has no code");
            return (0, 0);
        }
        try this.probeSafe(cfg.treasury) returns (uint256 t, uint256 n) {
            return (t, n);
        } catch {
            if (cfg.chainId == BASE) revert TreasuryIsNotASafe(cfg.treasury);
            _log("WARNING: the treasury does not answer the Safe probe (getThreshold, getOwners)");
        }
    }

    function _writeRecord(Config memory cfg, PFTToken token, address deployer, uint256 threshold, uint256 owners)
        private
    {
        string memory o = "pft_token_deployment";
        string memory toml = VM.readFile("foundry.toml");
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
        VM.serializeUint(o, "treasury_safe_threshold", threshold);
        VM.serializeUint(o, "treasury_safe_owner_count", owners);
        VM.serializeString(o, "solc_version", VM.parseTomlString(toml, ".profile.default.solc_version"));
        VM.serializeBool(o, "optimizer", VM.parseTomlBool(toml, ".profile.default.optimizer"));
        VM.serializeUint(o, "optimizer_runs", VM.parseTomlUint(toml, ".profile.default.optimizer_runs"));
        VM.serializeString(o, "evm_version", VM.parseTomlString(toml, ".profile.default.evm_version"));
        string memory json = VM.serializeString(o, "openzeppelin_commit", OPENZEPPELIN_COMMIT);
        VM.createDir(cfg.recordDir, true);
        string memory path = string.concat(cfg.recordDir, "/deployment.json");
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
