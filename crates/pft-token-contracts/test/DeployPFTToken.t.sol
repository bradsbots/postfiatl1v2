// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {PFTToken} from "../src/PFTToken.sol";
import {DeployPFTToken, ISafeProbe} from "../script/DeployPFTToken.s.sol";

interface IDeployTestVm {
    function chainId(uint256 newChainId) external;
    function etch(address target, bytes calldata newRuntimeBytecode) external;
    function store(address target, bytes32 slot, bytes32 value) external;
    function exists(string calldata path) external view returns (bool);
    function removeFile(string calldata path) external;
    function parseJsonBool(string calldata json, string calldata key) external pure returns (bool);
    function parseJsonAddressArray(string calldata json, string calldata key) external pure returns (address[] memory);
    function setNonce(address account, uint64 newNonce) external;
    function setNonceUnsafe(address account, uint64 newNonce) external;
    function setEnv(string calldata name, string calldata value) external;
    function expectRevert(bytes calldata revertData) external;
    function readFile(string calldata path) external view returns (string memory data);
    function parseJsonUint(string calldata json, string calldata key) external pure returns (uint256);
    function parseJsonString(string calldata json, string calldata key) external pure returns (string memory);
    function parseJsonAddress(string calldata json, string calldata key) external pure returns (address);
    function toString(address value) external pure returns (string memory);
    function toString(bytes calldata value) external pure returns (string memory);
}

/// A Safe as far as the probe can tell: threshold 2 of 3 owners. Slot 0 is the
/// proxy's singleton slot; a test or the CLI fixture sets it with vm.store.
contract FakeSafe is ISafeProbe {
    function getThreshold() external pure returns (uint256) {
        return 2;
    }

    function getOwners() external pure returns (address[] memory owners) {
        owners = new address[](3);
        owners[0] = address(0x0A1);
        owners[1] = address(0x0A2);
        owners[2] = address(0x0A3);
    }
}

/// Answers the probe with the values it is built with; slot 0 is the singleton.
contract ConfigurableSafe is ISafeProbe {
    address private singleton;
    uint256 private threshold;
    address[] private owners;

    constructor(address singleton_, uint256 threshold_, address[] memory owners_) {
        singleton = singleton_;
        threshold = threshold_;
        owners = owners_;
    }

    function getThreshold() external view returns (uint256) {
        return threshold;
    }

    function getOwners() external view returns (address[] memory) {
        return owners;
    }
}

/// Answers getOwners with returndata that is not an address[] encoding.
contract MalformedOwnersSafe {
    function getThreshold() external pure returns (uint256) {
        return 2;
    }

    fallback() external {
        assembly {
            mstore(0, 0x40) // wrong offset
            mstore(0x20, 1)
            return(0, 0x40)
        }
    }
}

/// Answers getThreshold with a short word.
contract ShortThresholdSafe {
    fallback() external {
        assembly {
            return(0, 1)
        }
    }
}

/// A contract without the Safe functions and without a fallback.
contract NotASafe {
    function ping() external pure returns (uint256) {
        return 1;
    }
}

/// The broadcaster. Forge counts every top-level call of the test contract as a
/// transaction of its own, so the test contract cannot stand in for a fresh key.
contract Broadcaster {
    function deploy(DeployPFTToken script, DeployPFTToken.Config memory cfg) external returns (PFTToken) {
        return script.deploy(cfg);
    }

    function run(DeployPFTToken script) external returns (PFTToken) {
        return script.run();
    }
}

contract DeployPFTTokenTest {
    IDeployTestVm private constant VM = IDeployTestVm(address(uint160(uint256(keccak256("hevm cheat code")))));

    uint256 private constant BASE = 8453;
    uint256 private constant BASE_SEPOLIA = 84532;
    address private constant TREASURY = address(0x5AFE);
    string private constant NAME = "Post Fiat Token";
    string private constant SYMBOL = "PFT";
    uint256 private constant SUPPLY_PFT = 1_000_000;
    uint256 private constant SUPPLY = SUPPLY_PFT * 1_000_000;
    /// Safe v1.4.1 SafeL2, the canonical deployment of safe-global/safe-deployments.
    address private constant SAFE_L2 = 0x29fcB43b46531BcA003ddC8FCB67FFE91900C762;
    string private constant COMMIT = "0123456789abcdef0123456789abcdef01234567";

    DeployPFTToken private script;
    Broadcaster private broadcaster;

    function setUp() public {
        script = new DeployPFTToken();
        broadcaster = new Broadcaster();
        VM.etch(TREASURY, address(new FakeSafe()).code);
        VM.store(TREASURY, bytes32(0), bytes32(uint256(uint160(SAFE_L2))));
        VM.setNonceUnsafe(address(broadcaster), 0);
        VM.chainId(BASE_SEPOLIA);
    }

    // ---------------------------------------------------------------- accepted

    function testDeploysOnBaseSepoliaAndWritesTheRecord() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.recordDir = "cache/deploy-test/base-sepolia";
        cfg.writeRecord = true;
        PFTToken token = broadcaster.deploy(script, cfg);
        _checkToken(token, NAME, SUPPLY);
        _checkRecord(cfg.recordDir, token, BASE_SEPOLIA, "test", SAFE_L2, 2, 3);
    }

    function testDeploysOnBaseMainnetAndWritesTheRecord() public {
        VM.chainId(BASE);
        DeployPFTToken.Config memory cfg = _config(BASE);
        cfg.recordDir = "cache/deploy-test/base";
        cfg.writeRecord = true;
        PFTToken token = broadcaster.deploy(script, cfg);
        _checkToken(token, NAME, SUPPLY);
        _checkRecord(cfg.recordDir, token, BASE, "test", SAFE_L2, 2, 3);
    }

    function testAcceptsAThirtyOneByteName() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.name = "Post Fiat Token on Base, 31 byt";
        _assertEq(bytes(cfg.name).length, 31, "fixture length");
        _checkToken(broadcaster.deploy(script, cfg), cfg.name, SUPPLY);
    }

    function testRunReadsTheEnvironment() public {
        // The only test that touches the process environment, so parallel
        // tests cannot race on it.
        VM.setEnv("PFT_TOKEN_CHAIN_ID", "84532");
        VM.setEnv("PFT_TOKEN_NAME", NAME);
        VM.setEnv("PFT_TOKEN_SYMBOL", SYMBOL);
        VM.setEnv("PFT_TOKEN_TOTAL_SUPPLY", "1000000000000");
        VM.setEnv("PFT_TOKEN_TOTAL_SUPPLY_PFT", "1000000");
        VM.setEnv("PFT_TOKEN_TREASURY", VM.toString(TREASURY));
        VM.setEnv("PFT_TOKEN_ALLOW_EOA_TREASURY", "");
        VM.setEnv("PFT_TOKEN_ALLOW_USED_DEPLOYER", "0");
        VM.setEnv("PFT_TOKEN_REAL_DEPLOYMENT", "");
        VM.setEnv("PFT_TOKEN_SOURCE_COMMIT", COMMIT);

        DeployPFTToken.Config memory cfg = script.readConfig();
        _assertEq(cfg.chainId, BASE_SEPOLIA, "chain id");
        _assertEq(cfg.totalSupplyPft, SUPPLY_PFT, "supply in PFT");
        _assertTrue(cfg.treasury == TREASURY, "treasury");
        _assertTrue(!cfg.allowEoaTreasury && !cfg.allowUsedDeployer && !cfg.realDeployment, "switches off");
        _assertTrue(!cfg.writeRecord, "no record outside a broadcast");
        _assertTrue(_eq(cfg.recordDir, "cache/deploy-test/pft-token-base-84532"), "test record path");
        _assertTrue(_eq(cfg.sourceCommit, COMMIT), "source commit");
        // The real-deployment switch alone selects the durable path.
        VM.setEnv("PFT_TOKEN_REAL_DEPLOYMENT", "true");
        _assertTrue(!script.readConfig().realDeployment, "only exactly 1 is on");
        VM.setEnv("PFT_TOKEN_REAL_DEPLOYMENT", "1");
        cfg = script.readConfig();
        _assertTrue(cfg.realDeployment, "real deployment");
        _assertTrue(_eq(cfg.recordDir, "deployments/pft-token-base-84532"), "durable record path");
        VM.setEnv("PFT_TOKEN_REAL_DEPLOYMENT", "");
        _checkToken(broadcaster.run(script), NAME, SUPPLY);

        VM.setEnv("PFT_TOKEN_ALLOW_EOA_TREASURY", "1");
        VM.setEnv("PFT_TOKEN_ALLOW_USED_DEPLOYER", "1");
        cfg = script.readConfig();
        _assertTrue(cfg.allowEoaTreasury && cfg.allowUsedDeployer, "switches on");
        VM.setEnv("PFT_TOKEN_REAL_DEPLOYMENT", "1");
        VM.expectRevert(
            abi.encodeWithSelector(DeployPFTToken.RealDeploymentWithTestSwitch.selector, "PFT_TOKEN_ALLOW_EOA_TREASURY")
        );
        broadcaster.run(script);
        VM.setEnv("PFT_TOKEN_REAL_DEPLOYMENT", "");

        VM.setEnv("PFT_TOKEN_TOTAL_SUPPLY_PFT", "REPLACE_with_whole_pft");
        VM.expectRevert(_placeholder("PFT_TOKEN_TOTAL_SUPPLY_PFT"));
        broadcaster.run(script);
        VM.setEnv("PFT_TOKEN_TOTAL_SUPPLY_PFT", " ");
        VM.expectRevert(_placeholder("PFT_TOKEN_TOTAL_SUPPLY_PFT"));
        broadcaster.run(script);
    }

    // -------------------------------------------------------------- chain id

    function testRefusesAChainOtherThanBase() public {
        VM.chainId(1);
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.UnsupportedChain.selector, 1));
        broadcaster.deploy(script, _config(1));
    }

    function testRefusesAChainIdMismatch() public {
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.WrongChain.selector, BASE, BASE_SEPOLIA));
        broadcaster.deploy(script, _config(BASE));
        VM.chainId(BASE);
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.WrongChain.selector, BASE_SEPOLIA, BASE));
        broadcaster.deploy(script, _config(BASE_SEPOLIA));
    }

    function testRefusesTheTestSwitchesOnBaseMainnet() public {
        VM.chainId(BASE);
        DeployPFTToken.Config memory cfg = _config(BASE);
        cfg.allowEoaTreasury = true;
        VM.expectRevert(
            abi.encodeWithSelector(DeployPFTToken.TestSwitchOnMainnet.selector, "PFT_TOKEN_ALLOW_EOA_TREASURY")
        );
        broadcaster.deploy(script, cfg);
        cfg = _config(BASE);
        cfg.allowUsedDeployer = true;
        VM.expectRevert(
            abi.encodeWithSelector(DeployPFTToken.TestSwitchOnMainnet.selector, "PFT_TOKEN_ALLOW_USED_DEPLOYER")
        );
        broadcaster.deploy(script, cfg);
    }

    // -------------------------------------------------------------- metadata

    function testRefusesPlaceholderNames() public {
        string[5] memory names = ["", "   ", "\t\n", "replace_with_token_name", "Post Fiat RePlAcE"];
        for (uint256 i = 0; i < names.length; i++) {
            DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
            cfg.name = names[i];
            VM.expectRevert(_placeholder("PFT_TOKEN_NAME"));
            broadcaster.deploy(script, cfg);
        }
    }

    function testRefusesPlaceholderSymbols() public {
        string[4] memory symbols = ["", " ", "REPLACE", "replace_with_token_symbol"];
        for (uint256 i = 0; i < symbols.length; i++) {
            DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
            cfg.symbol = symbols[i];
            VM.expectRevert(_placeholder("PFT_TOKEN_SYMBOL"));
            broadcaster.deploy(script, cfg);
        }
    }

    function testRefusesANameLongerThanThirtyOneBytes() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.name = "Post Fiat Token on Base, 32 byte";
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.NameTooLong.selector, 32));
        broadcaster.deploy(script, cfg);
        // The reason for the cap: OpenZeppelin's EIP712 keeps the name as a ShortString.
        VM.expectRevert(abi.encodeWithSignature("StringTooLong(string)", cfg.name));
        new PFTToken(cfg.name, SYMBOL, SUPPLY, TREASURY);
    }

    // ---------------------------------------------------------------- supply

    function testRefusesAZeroSupply() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.totalSupply = 0;
        cfg.totalSupplyPft = 0;
        VM.expectRevert(_placeholder("PFT_TOKEN_TOTAL_SUPPLY"));
        broadcaster.deploy(script, cfg);
    }

    function testRefusesASupplyMismatch() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.totalSupplyPft = SUPPLY; // units given twice: off by 10^6
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.SupplyMismatch.selector, SUPPLY, SUPPLY));
        broadcaster.deploy(script, cfg);
        cfg.totalSupplyPft = SUPPLY_PFT + 1;
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.SupplyMismatch.selector, SUPPLY, SUPPLY_PFT + 1));
        broadcaster.deploy(script, cfg);
        // A whole-PFT value whose unit count would overflow is a mismatch, not a panic.
        cfg.totalSupply = type(uint256).max;
        cfg.totalSupplyPft = type(uint256).max;
        VM.expectRevert(
            abi.encodeWithSelector(DeployPFTToken.SupplyMismatch.selector, type(uint256).max, type(uint256).max)
        );
        broadcaster.deploy(script, cfg);
    }

    // -------------------------------------------------------------- treasury

    function testRefusesAZeroTreasury() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.treasury = address(0);
        cfg.allowEoaTreasury = true;
        VM.expectRevert(_placeholder("PFT_TOKEN_TREASURY"));
        broadcaster.deploy(script, cfg);
    }

    function testRefusesTheDeployerAsTreasury() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.treasury = address(broadcaster);
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.TreasuryIsDeployer.selector, address(broadcaster)));
        broadcaster.deploy(script, cfg);
    }

    function testRefusesAnEoaTreasury() public {
        address eoa = address(0xE0A);
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.treasury = eoa;
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.TreasuryNotAContract.selector, eoa));
        broadcaster.deploy(script, cfg);
        VM.chainId(BASE);
        cfg.chainId = BASE;
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.TreasuryNotAContract.selector, eoa));
        broadcaster.deploy(script, cfg);
    }

    function testAllowsAnEoaTreasuryOnBaseSepoliaOnlyWithTheTestSwitch() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.treasury = address(0xE0A);
        cfg.allowEoaTreasury = true;
        cfg.recordDir = "cache/deploy-test/eoa-treasury";
        cfg.writeRecord = true;
        PFTToken token = broadcaster.deploy(script, cfg);
        _assertEq(token.balanceOf(address(0xE0A)), SUPPLY, "EOA treasury balance");
        _checkRecord(cfg.recordDir, token, BASE_SEPOLIA, "test", address(0), 0, 0);
    }

    function testTheEoaSwitchDoesNotRelaxTheSafeCheckOfAContract() public {
        VM.store(TREASURY, bytes32(0), bytes32(0));
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.allowEoaTreasury = true;
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.UnofficialSafeSingleton.selector, TREASURY, address(0)));
        broadcaster.deploy(script, cfg);
    }

    function testAcceptsEveryPinnedSingletonOnBothChains() public view {
        address[4] memory singletons = [
            0x41675C099F32341bf84BFc5382aF534df5C7461a,
            0x29fcB43b46531BcA003ddC8FCB67FFE91900C762,
            0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552,
            0x3E5c63644E683549055b9Be8653de26E0B4CD36E
        ];
        uint256[2] memory chains = [BASE, BASE_SEPOLIA];
        for (uint256 c = 0; c < chains.length; c++) {
            for (uint256 i = 0; i < singletons.length; i++) {
                _assertTrue(script.isOfficialSafeSingleton(chains[c], singletons[i]), "pinned singleton");
            }
            // The v1.3.0 eip155 deployment is listed for both chains but not pinned.
            _assertTrue(
                !script.isOfficialSafeSingleton(chains[c], 0xfb1bffC9d739B8D520DaF37dF666da4C687191EA), "eip155 L2"
            );
            _assertTrue(!script.isOfficialSafeSingleton(chains[c], address(0)), "zero singleton");
        }
        _assertTrue(!script.isOfficialSafeSingleton(1, singletons[0]), "other chain");
    }

    function testCheckSafeReadsTheSafe() public view {
        DeployPFTToken.SafeInfo memory safe = script.checkSafe(BASE_SEPOLIA, TREASURY);
        _assertTrue(safe.singleton == SAFE_L2, "singleton");
        _assertEq(safe.threshold, 2, "threshold");
        _assertEq(safe.owners.length, 3, "owners");
        _assertTrue(safe.owners[2] == address(0x0A3), "third owner");
    }

    function testRefusesALookalikeWithAWrongSingletonOnBothChains() public {
        address wrong = address(new FakeSafe()); // right answers, wrong singleton
        uint256[2] memory chains = [BASE, BASE_SEPOLIA];
        for (uint256 c = 0; c < chains.length; c++) {
            VM.chainId(chains[c]);
            VM.store(TREASURY, bytes32(0), bytes32(uint256(uint160(wrong))));
            VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.UnofficialSafeSingleton.selector, TREASURY, wrong));
            broadcaster.deploy(script, _config(chains[c]));
            // An official address with dirty upper bits is not the singleton.
            VM.store(TREASURY, bytes32(0), bytes32(uint256(uint160(SAFE_L2)) | (uint256(1) << 160)));
            VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.UnofficialSafeSingleton.selector, TREASURY, SAFE_L2));
            broadcaster.deploy(script, _config(chains[c]));
        }
    }

    function testRefusesAThresholdBelowTwoOnBothChains() public {
        address[] memory owners = new address[](3);
        (owners[0], owners[1], owners[2]) = (address(0x0A1), address(0x0A2), address(0x0A3));
        for (uint256 threshold = 0; threshold < 2; threshold++) {
            address safe = address(new ConfigurableSafe(SAFE_L2, threshold, owners));
            _assertTrue(script.isOfficialSafeSingleton(BASE, SAFE_L2), "fixture singleton");
            uint256[2] memory chains = [BASE, BASE_SEPOLIA];
            for (uint256 c = 0; c < chains.length; c++) {
                VM.chainId(chains[c]);
                DeployPFTToken.Config memory cfg = _config(chains[c]);
                cfg.treasury = safe;
                VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.SafeThresholdTooLow.selector, threshold));
                broadcaster.deploy(script, cfg);
            }
        }
    }

    function testRefusesSafeOwnersThatAreTooFewZeroRepeatedOrBelowTheThreshold() public {
        address[][4] memory sets;
        sets[0] = new address[](1);
        sets[0][0] = address(0x0A1);
        sets[1] = new address[](2);
        sets[1][0] = address(0x0A1); // sets[1][1] stays zero
        sets[2] = new address[](2);
        (sets[2][0], sets[2][1]) = (address(0x0A1), address(0x0A1));
        sets[3] = new address[](2);
        (sets[3][0], sets[3][1]) = (address(0x0A1), address(0x0A2));
        uint256[4] memory thresholds = [uint256(2), 2, 2, 3];
        uint256[4] memory distinct = [uint256(1), 1, 1, 2];
        for (uint256 i = 0; i < sets.length; i++) {
            DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
            cfg.treasury = address(new ConfigurableSafe(SAFE_L2, thresholds[i], sets[i]));
            VM.expectRevert(
                abi.encodeWithSelector(
                    DeployPFTToken.SafeOwnersInvalid.selector, sets[i].length, distinct[i], thresholds[i]
                )
            );
            broadcaster.deploy(script, cfg);
        }
    }

    function testRefusesATreasuryThatDoesNotAnswerTheProbeOnBothChains() public {
        bytes[4] memory codes = [
            address(new NotASafe()).code,
            address(new MalformedOwnersSafe()).code,
            address(new ShortThresholdSafe()).code,
            bytes(hex"00")
        ];
        uint256[2] memory chains = [BASE, BASE_SEPOLIA];
        for (uint256 c = 0; c < chains.length; c++) {
            VM.chainId(chains[c]);
            for (uint256 i = 0; i < codes.length; i++) {
                VM.etch(TREASURY, codes[i]);
                VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.TreasuryIsNotASafe.selector, TREASURY));
                broadcaster.deploy(script, _config(chains[c]));
            }
        }
    }

    // ------------------------------------------------------- deployment record

    function testRefusesARealDeploymentWithATestSwitch() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.realDeployment = true;
        cfg.allowEoaTreasury = true;
        VM.expectRevert(
            abi.encodeWithSelector(DeployPFTToken.RealDeploymentWithTestSwitch.selector, "PFT_TOKEN_ALLOW_EOA_TREASURY")
        );
        broadcaster.deploy(script, cfg);
        cfg.allowEoaTreasury = false;
        cfg.allowUsedDeployer = true;
        VM.expectRevert(
            abi.encodeWithSelector(
                DeployPFTToken.RealDeploymentWithTestSwitch.selector, "PFT_TOKEN_ALLOW_USED_DEPLOYER"
            )
        );
        broadcaster.deploy(script, cfg);
    }

    function testRealDeploymentWritesOnceAndRefusesToOverwrite() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.realDeployment = true;
        cfg.recordDir = "cache/deploy-test/real-once";
        cfg.writeRecord = true;
        cfg.sourceCommit = COMMIT;
        string memory path = string.concat(cfg.recordDir, "/deployment.json");
        if (VM.exists(path)) VM.removeFile(path);
        PFTToken token = broadcaster.deploy(script, cfg);
        _checkRecord(cfg.recordDir, token, BASE_SEPOLIA, "real", SAFE_L2, 2, 3);
        string memory json = VM.readFile(path);
        _assertTrue(_eq(VM.parseJsonString(json, ".source_commit"), COMMIT), "record source commit");

        // A second run, even a dry run that writes nothing, stops before deploying.
        VM.setNonceUnsafe(address(broadcaster), 0);
        cfg.writeRecord = false;
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.RecordExists.selector, path));
        broadcaster.deploy(script, cfg);
    }

    // -------------------------------------------------------------- deployer

    function testRefusesAUsedDeployer() public {
        VM.setNonce(address(broadcaster), 5);
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.DeployerAlreadyUsed.selector, address(broadcaster), 5));
        broadcaster.deploy(script, _config(BASE_SEPOLIA));
        VM.chainId(BASE);
        VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.DeployerAlreadyUsed.selector, address(broadcaster), 5));
        broadcaster.deploy(script, _config(BASE));
    }

    function testAllowsAUsedDeployerOnBaseSepoliaOnlyWithTheTestSwitch() public {
        VM.setNonce(address(broadcaster), 5);
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.allowUsedDeployer = true;
        _checkToken(broadcaster.deploy(script, cfg), NAME, SUPPLY);
    }

    // --------------------------------------------------------------- helpers

    function _config(uint256 chainId) private pure returns (DeployPFTToken.Config memory cfg) {
        cfg.chainId = chainId;
        cfg.name = NAME;
        cfg.symbol = SYMBOL;
        cfg.totalSupply = SUPPLY;
        cfg.totalSupplyPft = SUPPLY_PFT;
        cfg.treasury = TREASURY;
    }

    function _placeholder(string memory name) private pure returns (bytes memory) {
        return abi.encodeWithSelector(DeployPFTToken.PlaceholderValue.selector, name);
    }

    function _checkToken(PFTToken token, string memory name, uint256 supply) private view {
        _assertEq(token.totalSupply(), supply, "total supply");
        _assertEq(token.balanceOf(_treasuryOf(token)), supply, "treasury balance");
        _assertTrue(keccak256(bytes(token.name())) == keccak256(bytes(name)), "name");
        _assertTrue(keccak256(bytes(token.symbol())) == keccak256(bytes(SYMBOL)), "symbol");
        _assertEq(token.balanceOf(address(broadcaster)), 0, "deployer holds nothing");
    }

    /// The fixtures use either the Safe at TREASURY or the EOA 0xE0A.
    function _treasuryOf(PFTToken token) private view returns (address) {
        return token.balanceOf(TREASURY) > 0 ? TREASURY : address(0xE0A);
    }

    function _checkRecord(
        string memory dir,
        PFTToken token,
        uint256 chainId,
        string memory mode,
        address singleton,
        uint256 threshold,
        uint256 owners
    ) private view {
        string memory json = VM.readFile(string.concat(dir, "/deployment.json"));
        _assertTrue(_eq(VM.parseJsonString(json, ".mode"), mode), "record mode");
        _assertTrue(VM.parseJsonAddress(json, ".treasury_safe_singleton") == singleton, "record singleton");
        _assertEq(VM.parseJsonAddressArray(json, ".treasury_safe_owners").length, owners, "record owner list");
        _assertTrue(_eq(VM.parseJsonString(json, ".tx_hash"), "pending"), "record tx hash");
        _assertTrue(_eq(VM.parseJsonString(json, ".block_number"), "pending"), "record block number");
        _assertTrue(_eq(VM.parseJsonString(json, ".bytecode_hash"), "ipfs"), "record bytecode hash");
        _assertTrue(VM.parseJsonBool(json, ".cbor_metadata"), "record cbor metadata");
        _assertTrue(VM.parseJsonAddress(json, ".token") == address(token), "record token");
        _assertEq(VM.parseJsonUint(json, ".chain_id"), chainId, "record chain id");
        _assertTrue(_eq(VM.parseJsonString(json, ".name"), token.name()), "record name");
        _assertTrue(_eq(VM.parseJsonString(json, ".symbol"), SYMBOL), "record symbol");
        _assertEq(VM.parseJsonUint(json, ".total_supply_units"), SUPPLY, "record supply");
        _assertEq(VM.parseJsonUint(json, ".total_supply_pft"), SUPPLY_PFT, "record supply in PFT");
        _assertTrue(VM.parseJsonAddress(json, ".treasury") == _treasuryOf(token), "record treasury");
        _assertTrue(VM.parseJsonAddress(json, ".deployer") == address(broadcaster), "record deployer");
        _assertEq(VM.parseJsonUint(json, ".treasury_safe_threshold"), threshold, "record threshold");
        _assertEq(VM.parseJsonUint(json, ".treasury_safe_owner_count"), owners, "record owners");
        _assertTrue(_eq(VM.parseJsonString(json, ".solc_version"), "0.8.24"), "record solc");
        _assertTrue(_eq(VM.parseJsonString(json, ".evm_version"), "cancun"), "record evm version");
        _assertEq(VM.parseJsonUint(json, ".optimizer_runs"), 200, "record optimizer runs");
        _assertTrue(
            _eq(VM.parseJsonString(json, ".openzeppelin_commit"), "cab19933c33c2ad1d4c7a84864a3601dddfd16f3"),
            "record OpenZeppelin commit"
        );
        bytes memory args = abi.encode(token.name(), SYMBOL, SUPPLY, _treasuryOf(token));
        _assertTrue(_eq(VM.parseJsonString(json, ".constructor_args"), VM.toString(args)), "record constructor args");
    }

    function _eq(string memory a, string memory b) private pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }

    function _assertTrue(bool value, string memory message) private pure {
        if (!value) {
            revert(message);
        }
    }

    function _assertEq(uint256 actual, uint256 expected, string memory message) private pure {
        if (actual != expected) {
            revert(message);
        }
    }
}
