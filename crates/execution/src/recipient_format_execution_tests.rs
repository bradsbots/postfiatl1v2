    const RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT: u64 = 50;

    fn recipient_format_compatibility() -> AssetExecutionCompatibility {
        AssetExecutionCompatibility::strict().with_recipient_format_activation_height(Some(
            RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT,
        ))
    }

    /// Recipient strings that execution accepted before the rule and must
    /// reject after it, with the expected receipt code.
    fn recipient_format_rejection_cases() -> Vec<(String, &'static str)> {
        let derived = address_from_public_key(&ml_dsa_65_keygen_from_seed(&[1u8; 32]).public_key);
        let checksummed =
            postfiat_crypto_provider::checksum_address(&derived).expect("checksummed fixture");
        assert_ne!(checksummed, derived);
        let mut wrong_checksum = checksummed.clone().into_bytes();
        let letter = wrong_checksum
            .iter()
            .skip(2)
            .position(u8::is_ascii_alphabetic)
            .expect("fixture letter")
            + 2;
        wrong_checksum[letter] ^= 0x20;
        vec![
            ("pfrecipient".to_string(), "invalid_recipient_address"),
            (
                "bridge-recipient-000000000000000000000000".to_string(),
                "invalid_recipient_address",
            ),
            (format!("PF{}", &derived[2..]), "invalid_recipient_address"),
            (derived[..41].to_string(), "invalid_recipient_address"),
            (format!("{}g", &derived[..41]), "invalid_recipient_address"),
            (
                String::from_utf8(wrong_checksum).expect("ascii"),
                "invalid_recipient_checksum",
            ),
            (checksummed, "noncanonical_recipient_address"),
        ]
    }

    #[test]
    fn recipient_format_rule_is_inactive_by_default_in_every_compatibility_profile() {
        for compatibility in [
            AssetExecutionCompatibility::strict(),
            AssetExecutionCompatibility::wan_devnet_legacy_replay(),
            AssetExecutionCompatibility::wan_devnet_legacy_nav_replay(),
            AssetExecutionCompatibility::wan_devnet_legacy_cash_omitted_sp1_replay(),
            AssetExecutionCompatibility::wan_devnet_legacy_strict_domain_validation(),
        ] {
            assert_eq!(compatibility.recipient_format_activation_height, None);
            assert!(!compatibility.recipient_format_active(0));
            assert!(!compatibility.recipient_format_active(u64::MAX));
        }
        let scheduled = recipient_format_compatibility();
        assert!(!scheduled.recipient_format_active(RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT - 1));
        assert!(scheduled.recipient_format_active(RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT));
    }

    #[test]
    fn transfer_recipient_format_is_unchanged_before_activation_and_rejected_after() {
        let genesis = Genesis::new("postfiat-local");
        let key_pair = ml_dsa_65_keygen_from_seed(&[11u8; 32]);
        let from = address_from_public_key(&key_pair.public_key);
        let ledger = LedgerState::new(vec![Account::new(
            from.clone(),
            1_000,
            Some(bytes_to_hex(&key_pair.public_key)),
        )]);

        for (to, expected_code) in recipient_format_rejection_cases() {
            let transfer = signed_transfer_with_minimum_fee(&genesis, &key_pair, to.clone(), 25, 1);

            // Legacy behavior: the plain entrypoint credits the malformed key.
            let mut legacy_ledger = ledger.clone();
            let legacy = execute_transfer(&genesis, &mut legacy_ledger, &transfer);
            assert!(legacy.accepted, "{to}: {legacy:?}");
            assert_eq!(legacy_ledger.account(&to).expect("legacy credit").balance, 25);

            // No schedule, and a schedule that has not been reached, replay
            // exactly like the legacy entrypoint.
            for (compatibility, height) in [
                (AssetExecutionCompatibility::strict(), u64::MAX),
                (
                    recipient_format_compatibility(),
                    RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT - 1,
                ),
            ] {
                let mut replay_ledger = ledger.clone();
                let replay = execute_transfer_with_compatibility(
                    &genesis,
                    &mut replay_ledger,
                    &transfer,
                    height,
                    compatibility,
                );
                assert_eq!(replay, legacy, "{to}");
                assert_eq!(replay_ledger, legacy_ledger, "{to}");
            }

            // From the activation height the transfer is rejected, the sender
            // is not charged and its sequence is not consumed.
            let mut active_ledger = ledger.clone();
            let rejected = execute_transfer_with_compatibility(
                &genesis,
                &mut active_ledger,
                &transfer,
                RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT,
                recipient_format_compatibility(),
            );
            assert!(!rejected.accepted, "{to}");
            assert_eq!(rejected.code, expected_code, "{to}: {rejected:?}");
            assert!(rejected.message.contains("transfer.to"), "{rejected:?}");
            assert_eq!(rejected.tx_id, transfer_tx_id(&transfer));
            assert_eq!(rejected.fee_charged, 0);
            assert_eq!(active_ledger, ledger, "{to}");

            // Deterministic: the same input yields the same receipt.
            let mut again_ledger = ledger.clone();
            let again = execute_transfer_with_compatibility(
                &genesis,
                &mut again_ledger,
                &transfer,
                RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT + 1,
                recipient_format_compatibility(),
            );
            assert_eq!(again, rejected);
        }

        let recipient = address_from_public_key(&ml_dsa_65_keygen_from_seed(&[12u8; 32]).public_key);
        let valid = signed_transfer_with_minimum_fee(&genesis, &key_pair, recipient.clone(), 25, 1);
        let mut active_ledger = ledger.clone();
        let accepted = execute_transfer_with_compatibility(
            &genesis,
            &mut active_ledger,
            &valid,
            RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT,
            recipient_format_compatibility(),
        );
        assert!(accepted.accepted, "{accepted:?}");
        assert_eq!(active_ledger.account(&recipient).expect("credited").balance, 25);
    }

    #[test]
    fn payment_v2_recipient_format_is_unchanged_before_activation_and_rejected_after() {
        let genesis = Genesis::new("postfiat-local");
        let key_pair = ml_dsa_65_keygen_from_seed(&[13u8; 32]);
        let from = address_from_public_key(&key_pair.public_key);
        let ledger = LedgerState::new(vec![Account::new(
            from,
            1_000,
            Some(bytes_to_hex(&key_pair.public_key)),
        )]);
        let memo = PaymentMemo {
            memo_type: "74616700".to_string(),
            memo_format: String::new(),
            memo_data: "01".to_string(),
        };
        for (to, expected_code) in recipient_format_rejection_cases() {
            let payment = signed_payment_v2_with_minimum_fee(
                &genesis,
                &key_pair,
                to.clone(),
                30,
                1,
                vec![memo.clone()],
            );
            let mut legacy_ledger = ledger.clone();
            let legacy = execute_payment_v2(&genesis, &mut legacy_ledger, &payment);
            assert!(legacy.accepted, "{to}: {legacy:?}");

            let mut pre_ledger = ledger.clone();
            let pre = execute_payment_v2_with_compatibility(
                &genesis,
                &mut pre_ledger,
                &payment,
                RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT - 1,
                recipient_format_compatibility(),
            );
            assert_eq!(pre, legacy);
            assert_eq!(pre_ledger, legacy_ledger);

            let mut active_ledger = ledger.clone();
            let rejected = execute_payment_v2_with_compatibility(
                &genesis,
                &mut active_ledger,
                &payment,
                RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT,
                recipient_format_compatibility(),
            );
            assert!(!rejected.accepted);
            assert_eq!(rejected.code, expected_code, "{to}: {rejected:?}");
            assert!(rejected.message.contains("payment.to"), "{rejected:?}");
            assert_eq!(active_ledger, ledger);
        }
    }

    #[test]
    fn issued_payment_recipient_format_is_unchanged_before_activation_and_rejected_after() {
        let genesis = Genesis::new("postfiat-local");
        let issuer_key = ml_dsa_65_keygen_from_seed(&[14u8; 32]);
        let issuer = address_from_public_key(&issuer_key.public_key);
        let mut ledger = LedgerState::new(vec![Account::new(
            issuer.clone(),
            1_000,
            Some(bytes_to_hex(&issuer_key.public_key)),
        )]);
        let create = signed_asset_transaction_with_minimum_fee(
            &genesis,
            &ledger,
            &issuer_key,
            ASSET_CREATE_TRANSACTION_KIND,
            1,
            AssetTransactionOperation::AssetCreate(AssetCreateOperation {
                issuer: issuer.clone(),
                code: "USD".to_string(),
                version: 1,
                precision: 6,
                display_name: "US Dollar".to_string(),
                max_supply: Some(1_000),
                requires_authorization: false,
                freeze_enabled: false,
                clawback_enabled: false,
            }),
        );
        assert!(execute_asset_transaction(&genesis, &mut ledger, &create, 1).accepted);
        let asset_id = ledger.asset_definitions[0].asset_id.clone();
        // Issued payments require an existing recipient account, so model
        // keys that an earlier mistyped PFT transfer already created.
        let cases = recipient_format_rejection_cases();
        for (to, _) in &cases {
            ledger.ensure_account(to).balance = 100;
        }

        for (to, expected_code) in cases {
            let payment = signed_asset_transaction_with_minimum_fee(
                &genesis,
                &ledger,
                &issuer_key,
                ISSUED_PAYMENT_TRANSACTION_KIND,
                2,
                AssetTransactionOperation::IssuedPayment(IssuedPaymentOperation {
                    from: issuer.clone(),
                    to: to.clone(),
                    issuer: issuer.clone(),
                    asset_id: asset_id.clone(),
                    amount: 10,
                }),
            );
            let mut legacy_ledger = ledger.clone();
            let legacy = execute_asset_transaction_with_compatibility(
                &genesis,
                &mut legacy_ledger,
                &payment,
                RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT - 1,
                AssetExecutionCompatibility::strict(),
            );
            assert!(legacy.accepted, "{to}: {legacy:?}");

            let mut pre_ledger = ledger.clone();
            let pre = execute_asset_transaction_with_compatibility(
                &genesis,
                &mut pre_ledger,
                &payment,
                RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT - 1,
                recipient_format_compatibility(),
            );
            assert_eq!(pre, legacy);
            assert_eq!(pre_ledger, legacy_ledger);

            let mut active_ledger = ledger.clone();
            let rejected = execute_asset_transaction_with_compatibility(
                &genesis,
                &mut active_ledger,
                &payment,
                RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT,
                recipient_format_compatibility(),
            );
            assert!(!rejected.accepted);
            assert_eq!(rejected.code, expected_code, "{to}: {rejected:?}");
            assert!(rejected.message.contains("issued_payment.to"), "{rejected:?}");
            assert_eq!(active_ledger, ledger);
        }
    }

    #[test]
    fn escrow_and_nft_destinations_follow_the_recipient_format_rule() {
        let genesis = Genesis::new("postfiat-local");
        let key_pair = ml_dsa_65_keygen_from_seed(&[15u8; 32]);
        let owner = address_from_public_key(&key_pair.public_key);
        let ledger = LedgerState::new(vec![Account::new(
            owner.clone(),
            1_000,
            Some(bytes_to_hex(&key_pair.public_key)),
        )]);
        let malformed = "pfrecipient".to_string();

        let escrow = signed_escrow_transaction_with_minimum_fee(
            &genesis,
            &ledger,
            &key_pair,
            ESCROW_CREATE_TRANSACTION_KIND,
            1,
            EscrowTransactionOperation::EscrowCreate(EscrowCreateOperation {
                owner: owner.clone(),
                recipient: malformed.clone(),
                asset_id: NATIVE_PFT_ESCROW_ASSET_ID.to_string(),
                amount: 10,
                condition: String::new(),
                finish_after: 2,
                cancel_after: 0,
            }),
        );
        let mut legacy_ledger = ledger.clone();
        let legacy = execute_escrow_transaction(&genesis, &mut legacy_ledger, &escrow, 1);
        let mut pre_ledger = ledger.clone();
        let pre = execute_escrow_transaction_with_compatibility(
            &genesis,
            &mut pre_ledger,
            &escrow,
            1,
            recipient_format_compatibility(),
        );
        assert_eq!(pre, legacy);
        assert_eq!(pre_ledger, legacy_ledger);
        let mut active_ledger = ledger.clone();
        let rejected = execute_escrow_transaction_with_compatibility(
            &genesis,
            &mut active_ledger,
            &escrow,
            RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT,
            recipient_format_compatibility(),
        );
        assert_eq!(rejected.code, "invalid_recipient_address", "{rejected:?}");
        assert!(rejected.message.contains("escrow_create.recipient"));
        assert_eq!(active_ledger, ledger);

        let mint = signed_nft_transaction_with_minimum_fee(
            &genesis,
            &ledger,
            &key_pair,
            NFT_MINT_TRANSACTION_KIND,
            1,
            NftTransactionOperation::NftMint(NftMintOperation {
                issuer: owner.clone(),
                collection_id: "art".to_string(),
                serial: 1,
                owner: malformed.clone(),
                metadata_hash: "ab".repeat(32),
                metadata_uri: String::new(),
                flags: NFT_FLAG_TRANSFERABLE,
                collection_flags: 0,
                issuer_transfer_fee: 0,
            }),
        );
        let mut legacy_ledger = ledger.clone();
        let legacy = execute_nft_transaction(&genesis, &mut legacy_ledger, &mint);
        let mut pre_ledger = ledger.clone();
        let pre = execute_nft_transaction_with_compatibility(
            &genesis,
            &mut pre_ledger,
            &mint,
            1,
            recipient_format_compatibility(),
        );
        assert_eq!(pre, legacy);
        assert_eq!(pre_ledger, legacy_ledger);
        let mut active_ledger = ledger.clone();
        let rejected = execute_nft_transaction_with_compatibility(
            &genesis,
            &mut active_ledger,
            &mint,
            RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT,
            recipient_format_compatibility(),
        );
        assert_eq!(rejected.code, "invalid_recipient_address", "{rejected:?}");
        assert!(rejected.message.contains("nft_mint.owner"));
        assert_eq!(active_ledger, ledger);

        let nft_transfer = signed_nft_transaction_with_minimum_fee(
            &genesis,
            &ledger,
            &key_pair,
            NFT_TRANSFER_TRANSACTION_KIND,
            1,
            NftTransactionOperation::NftTransfer(NftTransferOperation {
                nft_id: "cd".repeat(postfiat_types::NFT_ID_HEX_LEN / 2),
                from: owner,
                to: malformed,
                issuer: String::new(),
                issuer_transfer_fee: 0,
            }),
        );
        let rejected = execute_nft_transaction_with_compatibility(
            &genesis,
            &mut ledger.clone(),
            &nft_transfer,
            RECIPIENT_FORMAT_TEST_ACTIVATION_HEIGHT,
            recipient_format_compatibility(),
        );
        assert_eq!(rejected.code, "invalid_recipient_address", "{rejected:?}");
        assert!(rejected.message.contains("nft_transfer.to"));
    }

    #[test]
    fn destination_address_rejection_bounds_untrusted_field_text() {
        let long = format!("pf{}\u{0007}", "z".repeat(200));
        let (code, message) =
            destination_address_rejection(&[("transfer.to", long.as_str())]).expect("rejected");
        assert_eq!(code, "invalid_recipient_address");
        assert!(message.len() < 200, "{message}");
        assert!(!message.contains('\u{0007}'));
        assert!(destination_address_rejection(&[(
            "transfer.to",
            "pfb385030ad80e5f7a59ec93b71f11055e9ccb9230"
        )])
        .is_none());
    }
