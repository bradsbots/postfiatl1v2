// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {PFTToken} from "../src/PFTToken.sol";

interface PFTTokenDeployVm {
    function envString(string calldata name) external view returns (string memory);
    function parseUint(string calldata value) external pure returns (uint256);
    function parseAddress(string calldata value) external pure returns (address);
    function startBroadcast() external;
    function stopBroadcast() external;
}

/// @notice Foundry deployment script for the fixed-supply PFT token on Base.
/// @dev No forge-std dependency is required; the script declares only the
///      cheatcodes it uses. PFT_TOKEN_NAME, PFT_TOKEN_SYMBOL,
///      PFT_TOKEN_TOTAL_SUPPLY (six-decimal units) and PFT_TOKEN_TREASURY come
///      from the environment. The RPC URL and the one-time deployer key are
///      given to `forge script` on the command line and are never read from a
///      file by this script.
contract DeployPFTToken {
    PFTTokenDeployVm private constant vm =
        PFTTokenDeployVm(address(uint160(uint256(keccak256("hevm cheat code")))));
    address private constant CONSOLE = 0x000000000000000000636F6e736F6c652e6c6f67;

    error PlaceholderValue(string name);

    event PFTTokenDeployed(
        address indexed token, address indexed treasury, uint256 total_supply, string name, string symbol
    );

    function run() external returns (PFTToken token) {
        string memory name = _required("PFT_TOKEN_NAME");
        string memory symbol = _required("PFT_TOKEN_SYMBOL");
        uint256 total_supply = vm.parseUint(_required("PFT_TOKEN_TOTAL_SUPPLY"));
        address treasury = vm.parseAddress(_required("PFT_TOKEN_TREASURY"));
        if (total_supply == 0) {
            revert PlaceholderValue("PFT_TOKEN_TOTAL_SUPPLY");
        }
        if (treasury == address(0)) {
            revert PlaceholderValue("PFT_TOKEN_TREASURY");
        }

        vm.startBroadcast();
        token = new PFTToken(name, symbol, total_supply, treasury);
        vm.stopBroadcast();

        emit PFTTokenDeployed(address(token), treasury, total_supply, name, symbol);
        _log("PFTToken deployed at", address(token));
    }

    /// Refuses an unset, empty or `replace...` placeholder value.
    function _required(string memory name) private view returns (string memory value) {
        value = vm.envString(name);
        if (bytes(value).length == 0 || _contains(bytes(value), bytes("replace"))) {
            revert PlaceholderValue(name);
        }
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

    function _log(string memory label, address value) private view {
        (bool ok,) = CONSOLE.staticcall(abi.encodeWithSignature("log(string,address)", label, value));
        ok;
    }
}
