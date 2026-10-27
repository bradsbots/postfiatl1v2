// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {PFTToken} from "../src/PFTToken.sol";
import {DeployPFTToken} from "../script/DeployPFTToken.s.sol";

interface IDeployTestVm {
    function chainId(uint256 newChainId) external;
    function etch(address target, bytes calldata newRuntimeBytecode) external;
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

/// A Safe as far as the read-only probe can tell: threshold 2 of 3 owners.
contract FakeSafe {
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

/// Answers the probe with a threshold no Safe can have.
contract ZeroThresholdSafe {
    function getThreshold() external pure returns (uint256) {
        return 0;
    }

    function getOwners() external pure returns (address[] memory owners) {
        owners = new address[](1);
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

    DeployPFTToken private script;
    Broadcaster private broadcaster;

    function setUp() public {
        script = new DeployPFTToken();
        broadcaster = new Broadcaster();
        VM.etch(TREASURY, address(new FakeSafe()).code);
        VM.setNonceUnsafe(address(broadcaster), 0);
        VM.chainId(BASE_SEPOLIA);
    }

    // ---------------------------------------------------------------- accepted

    function testDeploysOnBaseSepoliaAndWritesTheRecord() public {
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.recordDir = "cache/deploy-test/base-sepolia";
        PFTToken token = broadcaster.deploy(script, cfg);
        _checkToken(token, NAME, SUPPLY);
        _checkRecord(cfg.recordDir, token, BASE_SEPOLIA, 2, 3);
    }

    function testDeploysOnBaseMainnetAndWritesTheRecord() public {
        VM.chainId(BASE);
        DeployPFTToken.Config memory cfg = _config(BASE);
        cfg.recordDir = "cache/deploy-test/base";
        PFTToken token = broadcaster.deploy(script, cfg);
        _checkToken(token, NAME, SUPPLY);
        _checkRecord(cfg.recordDir, token, BASE, 2, 3);
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

        DeployPFTToken.Config memory cfg = script.readConfig();
        _assertEq(cfg.chainId, BASE_SEPOLIA, "chain id");
        _assertEq(cfg.totalSupplyPft, SUPPLY_PFT, "supply in PFT");
        _assertTrue(cfg.treasury == TREASURY, "treasury");
        _assertTrue(!cfg.allowEoaTreasury && !cfg.allowUsedDeployer, "switches off");
        _assertEq(bytes(cfg.recordDir).length, 0, "no record outside a broadcast");
        _checkToken(broadcaster.run(script), NAME, SUPPLY);

        VM.setEnv("PFT_TOKEN_ALLOW_EOA_TREASURY", "1");
        VM.setEnv("PFT_TOKEN_ALLOW_USED_DEPLOYER", "1");
        cfg = script.readConfig();
        _assertTrue(cfg.allowEoaTreasury && cfg.allowUsedDeployer, "switches on");

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
        PFTToken token = broadcaster.deploy(script, cfg);
        _assertEq(token.balanceOf(address(0xE0A)), SUPPLY, "EOA treasury balance");
        _checkRecord(cfg.recordDir, token, BASE_SEPOLIA, 0, 0);
    }

    function testRefusesATreasuryThatIsNotASafeOnBaseMainnet() public {
        VM.chainId(BASE);
        bytes[3] memory codes =
            [address(new NotASafe()).code, address(new ZeroThresholdSafe()).code, bytes(hex"00")];
        for (uint256 i = 0; i < codes.length; i++) {
            VM.etch(TREASURY, codes[i]);
            VM.expectRevert(abi.encodeWithSelector(DeployPFTToken.TreasuryIsNotASafe.selector, TREASURY));
            broadcaster.deploy(script, _config(BASE));
        }
    }

    function testWarnsOnATreasuryThatIsNotASafeOnBaseSepolia() public {
        VM.etch(TREASURY, address(new NotASafe()).code);
        DeployPFTToken.Config memory cfg = _config(BASE_SEPOLIA);
        cfg.recordDir = "cache/deploy-test/not-a-safe";
        PFTToken token = broadcaster.deploy(script, cfg);
        _checkToken(token, NAME, SUPPLY);
        _checkRecord(cfg.recordDir, token, BASE_SEPOLIA, 0, 0);
    }

    function testProbeReadsTheSafe() public view {
        (uint256 threshold, uint256 owners) = script.probeSafe(TREASURY);
        _assertEq(threshold, 2, "threshold");
        _assertEq(owners, 3, "owners");
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

    function _checkRecord(string memory dir, PFTToken token, uint256 chainId, uint256 threshold, uint256 owners)
        private
        view
    {
        string memory json = VM.readFile(string.concat(dir, "/deployment.json"));
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
