// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {DeployPFTToken} from "../script/DeployPFTToken.s.sol";
import {FakeSafe} from "./DeployPFTToken.t.sol";
import {SafeFixtures} from "./SafeFixtures.sol";

interface ICliFixtureVm {
    function envString(string calldata name) external view returns (string memory);
    function envOr(string calldata name, address defaultValue) external view returns (address);
    function envOr(string calldata name, bool defaultValue) external view returns (bool);
    function parseAddress(string calldata value) external pure returns (address);
    function etch(address target, bytes calldata newRuntimeBytecode) external;
    function store(address target, bytes32 slot, bytes32 value) external;
    function prank(address msgSender) external;
    function envOr(string calldata name, string calldata defaultValue) external view returns (string memory);
    function setEnv(string calldata name, string calldata value) external;
}

interface ICliSafeModules {
    function enableModule(address module) external;
}

/// The deploy script as `forge script` runs it, on forge's in-process chain,
/// with a code-bearing treasury: setUp places a real Safe (SafeL2 1.4.1 proxy,
/// 2 of 3) at PFT_TOKEN_TREASURY, then writes PFT_TOKEN_TEST_SINGLETON into its
/// slot 0 if set; PFT_TOKEN_TEST_MODULE enables that module on the Safe through
/// the Safe itself; PFT_TOKEN_TEST_FOUNDRY_OUT becomes FOUNDRY_OUT for the
/// script only (forge has already compiled); PFT_TOKEN_TEST_LOOKALIKE=true puts a FakeSafe with an allowed
/// slot 0 there instead. Run by test/deploy-script-cli.sh; never used for a
/// real deployment.
contract DeployPFTTokenWithFakeSafe is DeployPFTToken, SafeFixtures {
    ICliFixtureVm private constant FIXTURE_VM = ICliFixtureVm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function setUp() public {
        address treasury = FIXTURE_VM.parseAddress(FIXTURE_VM.envString("PFT_TOKEN_TREASURY"));
        _installSafeCode();
        _installSafe(treasury, FACTORY_1_4_1, SAFE_L2_1_4_1, _threeOwners(), 2);
        string memory out = FIXTURE_VM.envOr("PFT_TOKEN_TEST_FOUNDRY_OUT", string(""));
        if (bytes(out).length != 0) FIXTURE_VM.setEnv("FOUNDRY_OUT", out);
        address module = FIXTURE_VM.envOr("PFT_TOKEN_TEST_MODULE", address(0));
        if (module != address(0)) {
            FIXTURE_VM.prank(treasury);
            ICliSafeModules(treasury).enableModule(module);
        }
        address singleton = FIXTURE_VM.envOr("PFT_TOKEN_TEST_SINGLETON", SAFE_L2_1_4_1);
        if (FIXTURE_VM.envOr("PFT_TOKEN_TEST_LOOKALIKE", false)) {
            FIXTURE_VM.etch(treasury, type(FakeSafe).runtimeCode);
        }
        FIXTURE_VM.store(treasury, bytes32(0), bytes32(uint256(uint160(singleton))));
    }
}
