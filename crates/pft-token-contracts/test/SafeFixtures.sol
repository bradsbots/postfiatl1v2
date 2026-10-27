// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

interface ISafeFixtureVm {
    function readFile(string calldata path) external view returns (string memory);
    function parseBytes(string calldata value) external pure returns (bytes memory);
    function etch(address target, bytes calldata newRuntimeBytecode) external;
    function store(address target, bytes32 slot, bytes32 value) external;
}

interface ISafeSetup {
    function setup(
        address[] calldata owners,
        uint256 threshold,
        address to,
        bytes calldata data,
        address fallbackHandler,
        address paymentToken,
        uint256 payment,
        address payable paymentReceiver
    ) external;
}

interface ISafeProxyFactory {
    function createProxyWithNonce(address singleton, bytes memory initializer, uint256 saltNonce)
        external
        returns (address proxy);
}

/// Real Safe code on forge's in-process chain. test/fixtures/safe/*.runtime.hex
/// is the deployedBytecode of the npm packages safe-global/safe-contracts 1.4.1
/// and gnosis.pm/safe-contracts 1.3.0 (npm scopes); each file is checked on load against the
/// "canonical" codeHash in safe-global/safe-deployments b45417dd (the asset file
/// is named next to each constant). Proxies are made by the real factories, so
/// their code is what a canonical factory deploys.
abstract contract SafeFixtures {
    ISafeFixtureVm private constant SVM = ISafeFixtureVm(address(uint160(uint256(keccak256("hevm cheat code")))));

    // src/assets/v1.4.1/safe.json, safe_l2.json, src/assets/v1.3.0/gnosis_safe.json, gnosis_safe_l2.json
    address internal constant SINGLETON_1_4_1 = 0x41675C099F32341bf84BFc5382aF534df5C7461a;
    address internal constant SINGLETON_L2_1_4_1 = 0x29fcB43b46531BcA003ddC8FCB67FFE91900C762;
    address internal constant SINGLETON_1_3_0 = 0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552;
    address internal constant SINGLETON_L2_1_3_0 = 0x3E5c63644E683549055b9Be8653de26E0B4CD36E;
    bytes32 internal constant SINGLETON_1_4_1_HASH = 0x1fe2df852ba3299d6534ef416eefa406e56ced995bca886ab7a553e6d0c5e1c4;
    bytes32 internal constant SINGLETON_L2_1_4_1_HASH =
        0xb1f926978a0f44a2c0ec8fe822418ae969bd8c3f18d61e5103100339894f81ff;
    bytes32 internal constant SINGLETON_1_3_0_HASH = 0xbba688fbdb21ad2bb58bc320638b43d94e7d100f6f3ebaab0a4e4de6304b1c2e;
    bytes32 internal constant SINGLETON_L2_1_3_0_HASH =
        0x21842597390c4c6e3c1239e434a682b054bd9548eee5e9b1d6a4482731023c0f;
    // src/assets/v1.4.1/safe_proxy_factory.json, src/assets/v1.3.0/proxy_factory.json
    address internal constant FACTORY_1_4_1 = 0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67;
    address internal constant FACTORY_1_3_0 = 0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2;
    bytes32 internal constant FACTORY_1_4_1_HASH = 0x50c3cdc4074750a7a974204a716c999edd37482f907608d960b2b025ee0b3317;
    bytes32 internal constant FACTORY_1_3_0_HASH = 0x337d7f54be11b6ed55fef7b667ea5488db53db8320a05d1146aa4bd169a39a9b;

    uint256 private fixtureSalt;

    /// Etches the four singletons and both factories at their canonical addresses.
    function _installSafeCode() internal {
        _etchFixture(SINGLETON_1_4_1, "safe-1.4.1", SINGLETON_1_4_1_HASH);
        _etchFixture(SINGLETON_L2_1_4_1, "safe-l2-1.4.1", SINGLETON_L2_1_4_1_HASH);
        _etchFixture(SINGLETON_1_3_0, "gnosis-safe-1.3.0", SINGLETON_1_3_0_HASH);
        _etchFixture(SINGLETON_L2_1_3_0, "gnosis-safe-l2-1.3.0", SINGLETON_L2_1_3_0_HASH);
        _etchFixture(FACTORY_1_4_1, "safe-proxy-factory-1.4.1", FACTORY_1_4_1_HASH);
        _etchFixture(FACTORY_1_3_0, "gnosis-safe-proxy-factory-1.3.0", FACTORY_1_3_0_HASH);
    }

    /// A fresh proxy of `singleton` made by `factory`, not set up.
    function _newProxy(address factory, address singleton) internal returns (address) {
        uint256 salt = fixtureSalt++;
        return ISafeProxyFactory(factory).createProxyWithNonce(singleton, "", salt);
    }

    /// Places real proxy code at `at` pointing to `singleton` and, unless
    /// `threshold` is zero, sets the Safe up through the proxy.
    function _installSafe(address at, address factory, address singleton, address[] memory owners, uint256 threshold)
        internal
    {
        SVM.etch(at, _newProxy(factory, singleton).code);
        SVM.store(at, bytes32(0), bytes32(uint256(uint160(singleton))));
        if (threshold != 0) {
            ISafeSetup(at).setup(owners, threshold, address(0), "", address(0), address(0), 0, payable(address(0)));
        }
    }

    function _threeOwners() internal pure returns (address[] memory owners) {
        owners = new address[](3);
        (owners[0], owners[1], owners[2]) = (address(0x0A1), address(0x0A2), address(0x0A3));
    }

    function _etchFixture(address at, string memory name, bytes32 codehash) private {
        bytes memory code = SVM.parseBytes(SVM.readFile(string.concat("test/fixtures/safe/", name, ".runtime.hex")));
        require(keccak256(code) == codehash, string.concat("fixture code hash: ", name));
        SVM.etch(at, code);
    }
}
