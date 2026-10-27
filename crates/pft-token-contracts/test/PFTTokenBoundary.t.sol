// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {PFTToken} from "../src/PFTToken.sol";

interface IBoundaryVm {
    function addr(uint256 privateKey) external pure returns (address);
    function sign(uint256 privateKey, bytes32 digest) external pure returns (uint8 v, bytes32 r, bytes32 s);
    function prank(address sender) external;
    function warp(uint256 timestamp) external;
    function chainId(uint256 newChainId) external;
    function assume(bool condition) external pure;
    function expectRevert(bytes calldata revertData) external;
    function expectPartialRevert(bytes4 selector) external;
    function expectEmit(bool checkTopic1, bool checkTopic2, bool checkTopic3, bool checkData) external;
    function isContext(uint8 context) external view returns (bool);
    function exists(string calldata path) external view returns (bool);
    function readFile(string calldata path) external view returns (string memory);
    function parseJsonKeys(string calldata json, string calldata key) external pure returns (string[] memory);
}

/// The 13 functions the token is allowed to expose; its interfaceId is the XOR
/// of their selectors.
interface IPFTTokenABI {
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function decimals() external view returns (uint8);
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
    function nonces(address owner) external view returns (uint256);
    function DOMAIN_SEPARATOR() external view returns (bytes32);
    function eip712Domain()
        external
        view
        returns (bytes1, string memory, string memory, uint256, address, bytes32, uint256[] memory);
    function transfer(address to, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function approve(address spender, uint256 value) external returns (bool);
    function permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s)
        external;
}

contract PFTTokenBoundaryTest {
    IBoundaryVm private constant VM = IBoundaryVm(address(uint160(uint256(keccak256("hevm cheat code")))));

    event Transfer(address indexed from, address indexed to, uint256 value);

    string private constant NAME = "Post Fiat Token";
    string private constant SYMBOL = "PFT";
    uint256 private constant SUPPLY = 1_000_000_000_000;
    address private constant TREASURY = address(0x7EA5);
    address private constant ALICE = address(0xA11CE);
    address private constant BOB = address(0xB0B);
    // Foundry test keys; they never hold value outside the test EVM.
    uint256 private constant OWNER_KEY = 0x5EED;
    uint256 private constant OTHER_KEY = 0xBAD;
    /// `ForgeContext.Coverage` in forge-std's Vm.
    uint8 private constant COVERAGE = 2;
    address private constant CONSOLE = 0x000000000000000000636F6e736F6c652e6c6f67;
    string private constant ARTIFACT = "out/PFTToken.sol/PFTToken.json";
    uint256 private constant SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141;

    bytes32 private constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");
    bytes32 private constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");

    PFTToken private token;
    address private owner;

    function setUp() public {
        token = new PFTToken(NAME, SYMBOL, SUPPLY, TREASURY);
        owner = VM.addr(OWNER_KEY);
        VM.prank(TREASURY);
        token.transfer(owner, 1_000_000);
        VM.warp(1_000_000);
    }

    // ------------------------------------------------------------- transfers

    function testTransferToZeroAddressReverts() public {
        VM.prank(TREASURY);
        VM.expectRevert(abi.encodeWithSignature("ERC20InvalidReceiver(address)", address(0)));
        token.transfer(address(0), 1);
    }

    function testTransferAboveBalanceReverts() public {
        VM.prank(ALICE);
        VM.expectRevert(abi.encodeWithSignature("ERC20InsufficientBalance(address,uint256,uint256)", ALICE, 0, 1));
        token.transfer(BOB, 1);
        uint256 balance = token.balanceOf(TREASURY);
        VM.prank(TREASURY);
        VM.expectRevert(
            abi.encodeWithSignature("ERC20InsufficientBalance(address,uint256,uint256)", TREASURY, balance, balance + 1)
        );
        token.transfer(BOB, balance + 1);
    }

    function testSelfTransferChangesNothing() public {
        uint256 balance = token.balanceOf(TREASURY);
        VM.expectEmit(true, true, false, true);
        emit Transfer(TREASURY, TREASURY, balance);
        VM.prank(TREASURY);
        _assertTrue(token.transfer(TREASURY, balance), "self-transfer result");
        _assertEq(token.balanceOf(TREASURY), balance, "balance after self-transfer");
        _assertEq(token.totalSupply(), SUPPLY, "supply");
    }

    function testZeroAmountTransferChangesNothing() public {
        uint256 balance = token.balanceOf(TREASURY);
        VM.prank(TREASURY);
        _assertTrue(token.transfer(ALICE, 0), "zero transfer result");
        // An empty account can send zero too.
        VM.prank(BOB);
        _assertTrue(token.transfer(ALICE, 0), "zero transfer from an empty account");
        _assertEq(token.balanceOf(TREASURY), balance, "sender balance");
        _assertEq(token.balanceOf(ALICE), 0, "recipient balance");
        _assertEq(token.totalSupply(), SUPPLY, "supply");
    }

    // ------------------------------------------------------------ allowances

    function testApproveToZeroAddressReverts() public {
        VM.prank(TREASURY);
        VM.expectRevert(abi.encodeWithSignature("ERC20InvalidSpender(address)", address(0)));
        token.approve(address(0), 1);
    }

    function testTransferFromAboveAllowanceReverts() public {
        VM.prank(TREASURY);
        token.approve(ALICE, 500);
        VM.prank(ALICE);
        VM.expectRevert(abi.encodeWithSignature("ERC20InsufficientAllowance(address,uint256,uint256)", ALICE, 500, 501));
        token.transferFrom(TREASURY, BOB, 501);
        _assertEq(token.allowance(TREASURY, ALICE), 500, "allowance unchanged");
    }

    function testInfiniteAllowanceIsNotDecremented() public {
        VM.prank(TREASURY);
        token.approve(ALICE, type(uint256).max);
        VM.prank(ALICE);
        token.transferFrom(TREASURY, BOB, 750_000);
        _assertEq(token.allowance(TREASURY, ALICE), type(uint256).max, "infinite allowance");
        _assertEq(token.balanceOf(BOB), 750_000, "recipient balance");
    }

    function testApprovalOverwritesTheAllowance() public {
        VM.prank(TREASURY);
        token.approve(ALICE, 5);
        VM.prank(TREASURY);
        token.approve(ALICE, 3);
        _assertEq(token.allowance(TREASURY, ALICE), 3, "allowance is overwritten, not added");
    }

    // ---------------------------------------------------------------- permit

    function testPermitWithExpiredDeadlineReverts() public {
        uint256 deadline = block.timestamp - 1;
        (uint8 v, bytes32 r, bytes32 s) = _signPermit(OWNER_KEY, address(token), block.chainid, BOB, 1, 0, deadline);
        VM.expectRevert(abi.encodeWithSignature("ERC2612ExpiredSignature(uint256)", deadline));
        token.permit(owner, BOB, 1, deadline, v, r, s);
        _assertEq(token.nonces(owner), 0, "nonce after failed permit");
    }

    function testPermitFromAWrongSignerReverts() public {
        uint256 deadline = block.timestamp;
        // The owner's permit, signed with another key.
        (uint8 v, bytes32 r, bytes32 s) =
            VM.sign(OTHER_KEY, _permitDigest(address(token), block.chainid, BOB, 1, 0, deadline));
        VM.expectRevert(abi.encodeWithSignature("ERC2612InvalidSigner(address,address)", VM.addr(OTHER_KEY), owner));
        token.permit(owner, BOB, 1, deadline, v, r, s);
        _assertEq(token.nonces(owner), 0, "nonce after failed permit");
    }

    function testPermitWithHighSIsRefused() public {
        uint256 deadline = block.timestamp + 1;
        (uint8 v, bytes32 r, bytes32 s) = _signPermit(OWNER_KEY, address(token), block.chainid, BOB, 1, 0, deadline);
        // The malleable twin of a valid signature: s' = n - s, v flipped.
        bytes32 highS = bytes32(SECP256K1_N - uint256(s));
        VM.expectRevert(abi.encodeWithSignature("ECDSAInvalidSignatureS(bytes32)", highS));
        token.permit(owner, BOB, 1, deadline, v == 27 ? 28 : 27, r, highS);
        _assertEq(token.nonces(owner), 0, "nonce after failed permit");
        // The low-s original still works.
        token.permit(owner, BOB, 1, deadline, v, r, s);
        _assertEq(token.nonces(owner), 1, "nonce after permit");
    }

    function testPermitToZeroSpenderReverts() public {
        uint256 deadline = block.timestamp + 1;
        (uint8 v, bytes32 r, bytes32 s) =
            _signPermit(OWNER_KEY, address(token), block.chainid, address(0), 1, 0, deadline);
        VM.expectRevert(abi.encodeWithSignature("ERC20InvalidSpender(address)", address(0)));
        token.permit(owner, address(0), 1, deadline, v, r, s);
        _assertEq(token.nonces(owner), 0, "nonce after failed permit");
    }

    function testPermitSignedForAnotherChainIsRefused() public {
        uint256 deadline = block.timestamp + 1;
        (uint8 v, bytes32 r, bytes32 s) = _signPermit(OWNER_KEY, address(token), block.chainid, BOB, 1, 0, deadline);
        // A fork of the chain: same contract, new chain id.
        VM.chainId(block.chainid + 1);
        bytes32 forkDigest = _permitDigest(address(token), block.chainid, BOB, 1, 0, deadline);
        VM.expectRevert(
            abi.encodeWithSignature("ERC2612InvalidSigner(address,address)", ecrecover(forkDigest, v, r, s), owner)
        );
        token.permit(owner, BOB, 1, deadline, v, r, s);
        _assertEq(token.nonces(owner), 0, "nonce after failed permit");
    }

    function testPermitSignedForAnotherContractIsRefused() public {
        PFTToken twin = new PFTToken(NAME, SYMBOL, SUPPLY, TREASURY);
        uint256 deadline = block.timestamp + 1;
        (uint8 v, bytes32 r, bytes32 s) = _signPermit(OWNER_KEY, address(twin), block.chainid, BOB, 1, 0, deadline);
        bytes32 digest = _permitDigest(address(token), block.chainid, BOB, 1, 0, deadline);
        VM.expectRevert(
            abi.encodeWithSignature("ERC2612InvalidSigner(address,address)", ecrecover(digest, v, r, s), owner)
        );
        token.permit(owner, BOB, 1, deadline, v, r, s);
        _assertEq(token.nonces(owner), 0, "nonce after failed permit");
    }

    function testEip712DomainFields() public view {
        (
            bytes1 fields,
            string memory name,
            string memory version,
            uint256 chainId,
            address verifyingContract,
            bytes32 salt,
            uint256[] memory extensions
        ) = token.eip712Domain();
        _assertTrue(fields == hex"0f", "fields: name, version, chainId, verifyingContract");
        _assertTrue(keccak256(bytes(name)) == keccak256(bytes(NAME)), "domain name");
        _assertTrue(keccak256(bytes(version)) == keccak256("1"), "domain version");
        _assertEq(chainId, block.chainid, "domain chain id");
        _assertTrue(verifyingContract == address(token), "verifying contract");
        _assertTrue(salt == bytes32(0) && extensions.length == 0, "no salt, no extensions");
        bytes32 domain = keccak256(
            abi.encode(DOMAIN_TYPEHASH, keccak256(bytes(name)), keccak256(bytes(version)), chainId, verifyingContract)
        );
        _assertTrue(token.DOMAIN_SEPARATOR() == domain, "domain separator");
    }

    // ----------------------------------------------------------- constructor

    function testConstructorAcceptsSupplyOne() public {
        VM.expectEmit(true, true, false, true);
        emit Transfer(address(0), TREASURY, 1);
        PFTToken one = new PFTToken(NAME, SYMBOL, 1, TREASURY);
        _assertEq(one.totalSupply(), 1, "supply one");
        _assertEq(one.balanceOf(TREASURY), 1, "treasury balance");
    }

    function testConstructorAcceptsTheMaximumSupply() public {
        VM.expectEmit(true, true, false, true);
        emit Transfer(address(0), TREASURY, type(uint256).max);
        PFTToken max = new PFTToken(NAME, SYMBOL, type(uint256).max, TREASURY);
        _assertEq(max.totalSupply(), type(uint256).max, "maximum supply");
        _assertEq(max.balanceOf(TREASURY), type(uint256).max, "treasury balance");
    }

    // ------------------------------------------------------------------ ABI

    /// The deployed dispatcher answers exactly the 13 allowed selectors.
    function testExposesExactlyTheThirteenAllowedFunctions() public view {
        bytes4[13] memory expected = [
            IPFTTokenABI.name.selector,
            IPFTTokenABI.symbol.selector,
            IPFTTokenABI.decimals.selector,
            IPFTTokenABI.totalSupply.selector,
            IPFTTokenABI.balanceOf.selector,
            IPFTTokenABI.allowance.selector,
            IPFTTokenABI.nonces.selector,
            IPFTTokenABI.DOMAIN_SEPARATOR.selector,
            IPFTTokenABI.eip712Domain.selector,
            IPFTTokenABI.transfer.selector,
            IPFTTokenABI.transferFrom.selector,
            IPFTTokenABI.approve.selector,
            IPFTTokenABI.permit.selector
        ];
        bytes4 xor;
        for (uint256 i = 0; i < expected.length; i++) {
            xor ^= expected[i];
        }
        _assertTrue(xor == type(IPFTTokenABI).interfaceId, "expected list matches the interface");
        _assertTrue(expected[12] == bytes4(0xd505accf), "permit selector");

        (bytes4[] memory found, uint256 count) = _dispatchedSelectors(address(token).code);
        _assertEq(count, expected.length, "number of dispatched selectors");
        for (uint256 i = 0; i < expected.length; i++) {
            bool seen = false;
            for (uint256 j = 0; j < count; j++) {
                seen = seen || found[j] == expected[i];
            }
            _assertTrue(seen, "an allowed function is not dispatched");
        }

        // The compiler's own list. Coverage builds without the optimizer and
        // does not refresh this artifact, so the check is skipped there.
        if (VM.isContext(COVERAGE)) {
            _log("note: methodIdentifiers check skipped under forge coverage");
            return;
        }
        _assertTrue(VM.exists(ARTIFACT), "artifact out/PFTToken.sol/PFTToken.json missing");
        string[] memory signatures = VM.parseJsonKeys(VM.readFile(ARTIFACT), ".methodIdentifiers");
        _assertEq(signatures.length, expected.length, "number of methodIdentifiers");
        for (uint256 i = 0; i < signatures.length; i++) {
            bytes4 selector = bytes4(keccak256(bytes(signatures[i])));
            bool allowed = false;
            for (uint256 j = 0; j < expected.length; j++) {
                allowed = allowed || selector == expected[j];
            }
            _assertTrue(allowed, string.concat("method not in the allowlist: ", signatures[i]));
        }
    }

    /// A hand-built dispatcher: `name()` with PUSH4, the 0x00-prefixed
    /// hiddenMint178(address,uint256) (0x00fefee5) as solc emits it, PUSH3 0xfefee5,
    /// and a 0x0000-prefixed selector with PUSH2, followed by an empty CBOR length.
    function testScannerFindsSelectorsWithLeadingZeroBytes() public pure {
        _assertTrue(bytes4(keccak256("hiddenMint178(address,uint256)")) == bytes4(0x00fefee5), "fixture selector");
        bytes memory code = hex"60003560e01c80" hex"6306fdde03" hex"14" hex"610040" hex"57" hex"80" hex"62fefee5"
            hex"14" hex"610050" hex"57" hex"80" hex"611234" hex"14" hex"610060" hex"57" hex"6001" hex"6002" hex"00"
            hex"0000";
        (bytes4[] memory found, uint256 count) = _dispatchedSelectors(code);
        _assertEq(count, 3, "selectors found");
        _assertTrue(found[0] == bytes4(0x06fdde03), "PUSH4 selector");
        _assertTrue(found[1] == bytes4(0x00fefee5), "PUSH3 selector");
        _assertTrue(found[2] == bytes4(0x00001234), "PUSH2 selector");
    }

    // ------------------------------------------------------------------ fuzz

    function testFuzz_TransferMovesTheExactAmount(address to, uint256 amount) public {
        VM.assume(to != address(0) && to != TREASURY);
        uint256 balance = token.balanceOf(TREASURY);
        amount = amount % (balance + 1);
        uint256 before = token.balanceOf(to);
        VM.prank(TREASURY);
        token.transfer(to, amount);
        _assertEq(token.balanceOf(to), before + amount, "recipient balance");
        _assertEq(token.balanceOf(TREASURY), balance - amount, "sender balance");
        _assertEq(token.totalSupply(), SUPPLY, "supply");
    }

    function testFuzz_TransferAboveBalanceReverts(address to, uint256 excess) public {
        VM.assume(to != address(0));
        uint256 balance = token.balanceOf(TREASURY);
        uint256 amount = balance + 1 + excess % (type(uint256).max - balance);
        VM.prank(TREASURY);
        VM.expectRevert(
            abi.encodeWithSignature("ERC20InsufficientBalance(address,uint256,uint256)", TREASURY, balance, amount)
        );
        token.transfer(to, amount);
    }

    function testFuzz_TransferFromSpendsTheAllowance(address spender, address to, uint256 allowed, uint256 amount)
        public
    {
        VM.assume(spender != address(0) && to != address(0) && to != TREASURY);
        allowed = allowed % (type(uint256).max); // finite allowance
        amount = amount % (allowed + 1);
        VM.assume(amount <= token.balanceOf(TREASURY));
        uint256 before = token.balanceOf(to);
        VM.prank(TREASURY);
        token.approve(spender, allowed);
        VM.prank(spender);
        token.transferFrom(TREASURY, to, amount);
        _assertEq(token.allowance(TREASURY, spender), allowed - amount, "allowance left");
        _assertEq(token.balanceOf(to), before + amount, "recipient balance");
    }

    function testFuzz_PermitSetsTheAllowance(uint256 key, address spender, uint256 value, uint256 deadline) public {
        key = 1 + key % (SECP256K1_N - 1);
        VM.assume(spender != address(0));
        deadline = block.timestamp + deadline % (type(uint256).max - block.timestamp);
        address signer = VM.addr(key);
        uint256 nonce = token.nonces(signer);
        (uint8 v, bytes32 r, bytes32 s) =
            _signPermit(key, address(token), block.chainid, spender, value, nonce, deadline);
        token.permit(signer, spender, value, deadline, v, r, s);
        _assertEq(token.allowance(signer, spender), value, "permit allowance");
        _assertEq(token.nonces(signer), nonce + 1, "nonce after permit");
        // The same signature cannot be replayed.
        VM.expectPartialRevert(bytes4(keccak256("ERC2612InvalidSigner(address,address)")));
        token.permit(signer, spender, value, deadline, v, r, s);
    }

    function testFuzz_PermitAfterTheDeadlineReverts(uint256 key, uint256 value, uint256 deadline) public {
        key = 1 + key % (SECP256K1_N - 1);
        deadline = deadline % block.timestamp;
        address signer = VM.addr(key);
        (uint8 v, bytes32 r, bytes32 s) = _signPermit(key, address(token), block.chainid, BOB, value, 0, deadline);
        VM.expectRevert(abi.encodeWithSignature("ERC2612ExpiredSignature(uint256)", deadline));
        token.permit(signer, BOB, value, deadline, v, r, s);
        _assertEq(token.nonces(signer), 0, "nonce after failed permit");
    }

    // --------------------------------------------------------------- helpers

    function _permitDigest(
        address verifyingContract,
        uint256 chainId,
        address spender,
        uint256 value,
        uint256 nonce,
        uint256 deadline
    ) private view returns (bytes32) {
        return _digest(verifyingContract, chainId, owner, spender, value, nonce, deadline);
    }

    function _digest(
        address verifyingContract,
        uint256 chainId,
        address signer,
        address spender,
        uint256 value,
        uint256 nonce,
        uint256 deadline
    ) private pure returns (bytes32) {
        bytes32 domain = keccak256(
            abi.encode(DOMAIN_TYPEHASH, keccak256(bytes(NAME)), keccak256("1"), chainId, verifyingContract)
        );
        bytes32 structHash = keccak256(abi.encode(PERMIT_TYPEHASH, signer, spender, value, nonce, deadline));
        return keccak256(abi.encodePacked("\x19\x01", domain, structHash));
    }

    function _signPermit(
        uint256 key,
        address verifyingContract,
        uint256 chainId,
        address spender,
        uint256 value,
        uint256 nonce,
        uint256 deadline
    ) private pure returns (uint8, bytes32, bytes32) {
        address signer = VM.addr(key);
        return VM.sign(key, _digest(verifyingContract, chainId, signer, spender, value, nonce, deadline));
    }

    /// Walks the runtime code (without the CBOR metadata) and collects every
    /// `PUSHn <selector> EQ` (n = 1..4), the dispatcher's comparison of the call
    /// selector, normalised to 4 bytes: solc drops a selector's leading zero
    /// bytes, so 0x00fefee5 is pushed with PUSH3.
    function _dispatchedSelectors(bytes memory code) private pure returns (bytes4[] memory found, uint256 count) {
        uint256 end = code.length;
        uint256 metadata = (uint256(uint8(code[end - 2])) << 8) | uint8(code[end - 1]);
        if (metadata + 2 <= end) {
            end -= metadata + 2;
        }
        found = new bytes4[](64);
        for (uint256 i = 0; i < end; i++) {
            uint8 op = uint8(code[i]);
            if (op >= 0x60 && op <= 0x63) {
                uint256 n = op - 0x5f;
                if (i + n + 1 < end && uint8(code[i + n + 1]) == 0x14) {
                    uint32 value = 0;
                    for (uint256 k = 1; k <= n; k++) {
                        value = (value << 8) | uint8(code[i + k]);
                    }
                    found[count++] = bytes4(value);
                }
            }
            if (op >= 0x60 && op <= 0x7f) {
                i += op - 0x5f; // skip the push data
            }
        }
    }

    function _log(string memory message) private view {
        (bool ok,) = CONSOLE.staticcall(abi.encodeWithSignature("log(string)", message));
        ok;
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
