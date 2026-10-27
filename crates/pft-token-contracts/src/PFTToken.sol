// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity 0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";

/// @title PFTToken
/// @notice The ERC-20 representation of PFT on Base.
///         - Fixed supply: the whole supply is minted once, in the constructor, to
///           the treasury. No function can mint, burn or otherwise change it later.
///         - Six decimals: one token unit equals one atom of native PFT, so
///           1 PFT = 1,000,000 units.
///         - No privileged role: there is no owner, admin, pause, blacklist, hook
///           or upgrade path; the deployer holds nothing after construction.
///         - Permit: holders can approve a spender with a signed message
///           (EIP-2612) instead of a transaction.
/// @dev Plain OpenZeppelin ERC20 and ERC20Permit. The name, symbol, total
///      supply and treasury (meant to be a Safe multisig) are constructor
///      arguments, so the contract fixes no supply number.
contract PFTToken is ERC20, ERC20Permit {
    error ZeroTreasury();
    error ZeroSupply();

    constructor(string memory name_, string memory symbol_, uint256 totalSupply_, address treasury_)
        ERC20(name_, symbol_)
        ERC20Permit(name_)
    {
        if (treasury_ == address(0)) {
            revert ZeroTreasury();
        }
        if (totalSupply_ == 0) {
            revert ZeroSupply();
        }
        _mint(treasury_, totalSupply_);
    }

    /// @notice Six decimals, the unit of native PFT.
    function decimals() public pure override returns (uint8) {
        return 6;
    }
}
