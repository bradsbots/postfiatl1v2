// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {PFTToken} from "../src/PFTToken.sol";

interface IInvariantVm {
    function addr(uint256 privateKey) external pure returns (address);
    function sign(uint256 privateKey, bytes32 digest) external pure returns (uint8 v, bytes32 r, bytes32 s);
    function prank(address sender) external;
}

/// Random transfers, approvals, transferFroms and permits between five actors;
/// the first actor is the treasury that received the whole supply.
contract PFTTokenHandler {
    IInvariantVm private constant VM = IInvariantVm(address(uint160(uint256(keccak256("hevm cheat code")))));
    bytes32 private constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    PFTToken public immutable token;
    uint256[5] private keys = [uint256(0xA1), 0xA2, 0xA3, 0xA4, 0xA5];
    address[5] public actors;
    uint256 public sentFromTreasury;
    uint256 public receivedByTreasury;
    uint256 public calls;

    constructor(uint256 supply) {
        for (uint256 i = 0; i < keys.length; i++) {
            actors[i] = VM.addr(keys[i]);
        }
        token = new PFTToken("Post Fiat Token", "PFT", supply, actors[0]);
    }

    function transfer(uint256 fromSeed, uint256 toSeed, uint256 amount) external {
        (address from, address to) = (_actor(fromSeed), _actor(toSeed));
        amount = amount % (token.balanceOf(from) + 1);
        VM.prank(from);
        token.transfer(to, amount);
        _track(from, to, amount);
    }

    function approve(uint256 ownerSeed, uint256 spenderSeed, uint256 amount) external {
        VM.prank(_actor(ownerSeed));
        token.approve(_actor(spenderSeed), amount);
        calls++;
    }

    function transferFrom(uint256 spenderSeed, uint256 fromSeed, uint256 toSeed, uint256 amount) external {
        (address spender, address from, address to) = (_actor(spenderSeed), _actor(fromSeed), _actor(toSeed));
        uint256 limit = token.balanceOf(from);
        uint256 allowed = token.allowance(from, spender);
        amount = amount % ((allowed < limit ? allowed : limit) + 1);
        VM.prank(spender);
        token.transferFrom(from, to, amount);
        _track(from, to, amount);
    }

    function permit(uint256 ownerSeed, uint256 spenderSeed, uint256 value, uint256 lifetime) external {
        uint256 i = ownerSeed % keys.length;
        address owner = actors[i];
        address spender = _actor(spenderSeed);
        uint256 deadline = block.timestamp + lifetime % 365 days;
        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                token.DOMAIN_SEPARATOR(),
                keccak256(abi.encode(PERMIT_TYPEHASH, owner, spender, value, token.nonces(owner), deadline))
            )
        );
        (uint8 v, bytes32 r, bytes32 s) = VM.sign(keys[i], digest);
        token.permit(owner, spender, value, deadline, v, r, s);
        calls++;
    }

    function actorCount() external view returns (uint256) {
        return actors.length;
    }

    function _actor(uint256 seed) private view returns (address) {
        return actors[seed % actors.length];
    }

    function _track(address from, address to, uint256 amount) private {
        if (from == actors[0] && to != actors[0]) sentFromTreasury += amount;
        if (to == actors[0] && from != actors[0]) receivedByTreasury += amount;
        calls++;
    }
}

contract PFTTokenInvariantTest {
    uint256 private constant SUPPLY = 1_000_000_000_000;

    PFTTokenHandler private handler;
    PFTToken private token;

    function setUp() public {
        handler = new PFTTokenHandler(SUPPLY);
        token = handler.token();
    }

    /// Only the handler is called; forge reads this like forge-std's targetContract.
    function targetContracts() public view returns (address[] memory targets) {
        targets = new address[](1);
        targets[0] = address(handler);
    }

    function invariant_SumOfBalancesEqualsTotalSupply() public view {
        uint256 sum = 0;
        for (uint256 i = 0; i < handler.actorCount(); i++) {
            sum += token.balanceOf(handler.actors(i));
        }
        _assertEq(sum, token.totalSupply(), "sum of balances");
    }

    function invariant_TotalSupplyNeverChanges() public view {
        _assertEq(token.totalSupply(), SUPPLY, "total supply");
    }

    /// With fail_on_revert every handler call must succeed; this proves calls
    /// were made. Forge also checks each invariant_* once after setUp, before
    /// any call, so this one runs from the afterInvariant hook, at the end of
    /// every run (HandlerMadeCalls).
    function afterInvariant() public view {
        _assertTrue(handler.calls() > 0, "the handler made no calls");
    }

    function invariant_TreasuryBalancePlusNetOutflowEqualsSupply() public view {
        uint256 treasury = token.balanceOf(handler.actors(0));
        _assertEq(treasury + handler.sentFromTreasury() - handler.receivedByTreasury(), SUPPLY, "treasury flow");
    }

    function _assertEq(uint256 actual, uint256 expected, string memory message) private pure {
        if (actual != expected) {
            revert(message);
        }
    }

    function _assertTrue(bool value, string memory message) private pure {
        if (!value) {
            revert(message);
        }
    }
}
