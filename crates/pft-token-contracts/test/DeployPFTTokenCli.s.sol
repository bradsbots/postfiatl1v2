// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {DeployPFTToken} from "../script/DeployPFTToken.s.sol";
import {FakeSafe} from "./DeployPFTToken.t.sol";

interface ICliFixtureVm {
    function envString(string calldata name) external view returns (string memory);
    function envOr(string calldata name, address defaultValue) external view returns (address);
    function parseAddress(string calldata value) external pure returns (address);
    function etch(address target, bytes calldata newRuntimeBytecode) external;
    function store(address target, bytes32 slot, bytes32 value) external;
}

/// The deploy script as `forge script` runs it, on forge's in-process chain,
/// with a code-bearing treasury: setUp places a FakeSafe at PFT_TOKEN_TREASURY
/// and writes PFT_TOKEN_TEST_SINGLETON (default: Safe v1.4.1 SafeL2) into its
/// slot 0. Run by test/deploy-script-cli.sh; never used for a real deployment.
contract DeployPFTTokenWithFakeSafe is DeployPFTToken {
    ICliFixtureVm private constant FIXTURE_VM = ICliFixtureVm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function setUp() public {
        address treasury = FIXTURE_VM.parseAddress(FIXTURE_VM.envString("PFT_TOKEN_TREASURY"));
        address singleton = FIXTURE_VM.envOr("PFT_TOKEN_TEST_SINGLETON", SAFE_L2_1_4_1);
        FIXTURE_VM.etch(treasury, type(FakeSafe).runtimeCode);
        FIXTURE_VM.store(treasury, bytes32(0), bytes32(uint256(uint160(singleton))));
    }
}
