// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {PFTToken} from "../src/PFTToken.sol";

interface VmPFTToken {
    function addr(uint256 privateKey) external pure returns (address);
    function sign(uint256 privateKey, bytes32 digest) external pure returns (uint8 v, bytes32 r, bytes32 s);
    function prank(address sender) external;
    function expectRevert() external;
    function expectRevert(bytes4 selector) external;
}

/// The token is reached through this interface so the tests compile against
/// any contract named PFTToken with the four-argument constructor.
interface IPFTTokenUnderTest {
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function decimals() external view returns (uint8);
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
    function transfer(address to, uint256 value) external returns (bool);
    function approve(address spender, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function nonces(address owner) external view returns (uint256);
    function DOMAIN_SEPARATOR() external view returns (bytes32);
    function permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s)
        external;
}

contract PFTTokenTest {
    VmPFTToken private constant vm = VmPFTToken(address(uint160(uint256(keccak256("hevm cheat code")))));

    string private constant NAME = "Post Fiat Token";
    string private constant SYMBOL = "PFT";
    // A test amount only; the product owner has not decided the real supply.
    uint256 private constant SUPPLY = 1_000_000_000_000;
    address private constant TREASURY = address(0x7EA5);
    address private constant ALICE = address(0xA11CE);
    address private constant BOB = address(0xB0B);
    // Foundry test key for the permit signature; it never holds value outside the test EVM.
    uint256 private constant PERMIT_OWNER_KEY = 0x5EED;

    bytes32 private constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");
    bytes32 private constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");

    function testTotalSupplyEqualsArgumentAndSitsWithTreasury() public {
        IPFTTokenUnderTest token = _deploy();
        _assertEq(token.totalSupply(), SUPPLY, "total supply");
        _assertEq(token.balanceOf(TREASURY), SUPPLY, "treasury balance");
        _assertEq(token.balanceOf(address(this)), 0, "deployer balance");
        _assertTrue(keccak256(bytes(token.name())) == keccak256(bytes(NAME)), "name");
        _assertTrue(keccak256(bytes(token.symbol())) == keccak256(bytes(SYMBOL)), "symbol");
    }

    function testDecimalsIsSix() public {
        _assertEq(_deploy().decimals(), 6, "decimals");
    }

    function testTransferMovesBalance() public {
        IPFTTokenUnderTest token = _deploy();
        vm.prank(TREASURY);
        _assertTrue(token.transfer(ALICE, 1_500_000), "transfer result");
        _assertEq(token.balanceOf(ALICE), 1_500_000, "recipient balance");
        _assertEq(token.balanceOf(TREASURY), SUPPLY - 1_500_000, "treasury balance");
        _assertEq(token.totalSupply(), SUPPLY, "supply unchanged");
    }

    function testApproveAndTransferFrom() public {
        IPFTTokenUnderTest token = _deploy();
        vm.prank(TREASURY);
        _assertTrue(token.approve(ALICE, 2_000_000), "approve result");
        _assertEq(token.allowance(TREASURY, ALICE), 2_000_000, "allowance");
        vm.prank(ALICE);
        _assertTrue(token.transferFrom(TREASURY, BOB, 750_000), "transferFrom result");
        _assertEq(token.balanceOf(BOB), 750_000, "recipient balance");
        _assertEq(token.allowance(TREASURY, ALICE), 1_250_000, "allowance left");
        vm.prank(ALICE);
        vm.expectRevert();
        token.transferFrom(TREASURY, BOB, 1_250_001);
    }

    function testPermitWithSignedMessage() public {
        IPFTTokenUnderTest token = _deploy();
        address owner = vm.addr(PERMIT_OWNER_KEY);
        vm.prank(TREASURY);
        token.transfer(owner, 1_000_000);

        bytes32 domain = keccak256(
            abi.encode(DOMAIN_TYPEHASH, keccak256(bytes(NAME)), keccak256("1"), block.chainid, address(token))
        );
        _assertTrue(token.DOMAIN_SEPARATOR() == domain, "domain separator");
        uint256 deadline = block.timestamp + 1 hours;
        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01", domain, keccak256(abi.encode(PERMIT_TYPEHASH, owner, BOB, 400_000, 0, deadline))
            )
        );
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(PERMIT_OWNER_KEY, digest);

        token.permit(owner, BOB, 400_000, deadline, v, r, s);
        _assertEq(token.allowance(owner, BOB), 400_000, "permit allowance");
        _assertEq(token.nonces(owner), 1, "nonce after permit");
        vm.prank(BOB);
        token.transferFrom(owner, BOB, 400_000);
        _assertEq(token.balanceOf(BOB), 400_000, "spender balance");

        // The same signature cannot be used twice.
        vm.expectRevert();
        token.permit(owner, BOB, 400_000, deadline, v, r, s);
    }

    function testHasNoMintPauseOwnerBlacklistOrUpgradeFunction() public {
        IPFTTokenUnderTest token = _deploy();
        bytes[12] memory calls = [
            abi.encodeWithSignature("mint(address,uint256)", address(this), 1),
            abi.encodeWithSignature("mint(uint256)", 1),
            abi.encodeWithSignature("burn(uint256)", 1),
            abi.encodeWithSignature("pause()"),
            abi.encodeWithSignature("unpause()"),
            abi.encodeWithSignature("paused()"),
            abi.encodeWithSignature("owner()"),
            abi.encodeWithSignature("transferOwnership(address)", address(this)),
            abi.encodeWithSignature("renounceOwnership()"),
            abi.encodeWithSignature("blacklist(address)", ALICE),
            abi.encodeWithSignature("grantRole(bytes32,address)", bytes32(0), address(this)),
            abi.encodeWithSignature("upgradeToAndCall(address,bytes)", address(this), "")
        ];
        for (uint256 i = 0; i < calls.length; i++) {
            (bool ok, bytes memory returned) = address(token).call(calls[i]);
            // An unknown selector on a contract without a fallback reverts with no data.
            _assertTrue(!ok && returned.length == 0, "privileged selector answered");
        }
        _assertEq(token.totalSupply(), SUPPLY, "supply unchanged");
        _assertEq(token.balanceOf(TREASURY), SUPPLY, "treasury balance unchanged");
    }

    function testZeroTreasuryReverts() public {
        vm.expectRevert(bytes4(keccak256("ZeroTreasury()")));
        new PFTToken(NAME, SYMBOL, SUPPLY, address(0));
    }

    function testZeroSupplyReverts() public {
        vm.expectRevert(bytes4(keccak256("ZeroSupply()")));
        new PFTToken(NAME, SYMBOL, 0, TREASURY);
    }

    function _deploy() private returns (IPFTTokenUnderTest) {
        return IPFTTokenUnderTest(address(new PFTToken(NAME, SYMBOL, SUPPLY, TREASURY)));
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
