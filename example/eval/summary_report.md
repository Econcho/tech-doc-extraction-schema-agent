# Summary Report

## Dataset
- dataset_name: kep_all_labeled
- version: v1
- domain: kep
- schema_version: kep_schema_v2
- label_policy_version: registry_label_files
- split: kep_all_labeled
- doc_count: 54
- registry_path: F:\LLM\langextract-main\eval_system\dataset\KEP\registry_all.json

## Run
- prediction_path: F:\LLM\langextract-main\result\KEP_prompt_v2
- adapter: langextract
- matcher: max_weight_bipartite
- metrics: ['detection_strict', 'detection_relaxed', 'class_strict', 'class_relaxed', 'structured_strict', 'structured_relaxed', 'structure_anomaly_rate', 'grounding_match_exact_rate', 'grounding_match_lesser_rate', 'grounding_match_fuzzy_rate', 'grounding_match_none_rate']
- matching_metrics: ['detection_strict', 'detection_relaxed', 'class_strict', 'class_relaxed', 'structured_strict', 'structured_relaxed']
- diagnostic_metrics: ['structure_anomaly_rate', 'grounding_match_exact_rate', 'grounding_match_lesser_rate', 'grounding_match_fuzzy_rate', 'grounding_match_none_rate']
- thresholds: {'text_relaxed_f1': 0.8, 'substring_precision': 0.8, 'substring_recall': 0.8, 'lccs_ratio': 0.7}
- tokenizer_name: RegexTokenizer

## Micro Results
- detection_strict: P=0.8270, R=0.8033, F1=0.8150
- detection_relaxed: P=0.8620, R=0.8344, F1=0.8480
- class_strict: P=0.7930, R=0.7713, F1=0.7820
- class_relaxed: P=0.8240, R=0.7984, F1=0.8110
- structured_strict: P=0.7435, R=0.7238, F1=0.7335
- structured_relaxed: P=0.7780, R=0.7544, F1=0.7660
## Macro Doc Results
- detection_strict: P=0.8280, R=0.8043, F1=0.8160
- detection_relaxed: P=0.8630, R=0.8354, F1=0.8490
- class_strict: P=0.7940, R=0.7723, F1=0.7830
- class_relaxed: P=0.8250, R=0.7994, F1=0.8120
- structured_strict: P=0.7455, R=0.7258, F1=0.7355
- structured_relaxed: P=0.7790, R=0.7554, F1=0.7670
## Macro Class Results
### detection_strict
- summary: P=0.8221, R=0.7985, F1=0.8101
- motivation: P=0.8221, R=0.7985, F1=0.8101
- goal: P=0.8244, R=0.8008, F1=0.8124
- non_goal: P=0.8268, R=0.8032, F1=0.8148
- design_decision: P=0.8270, R=0.8033, F1=0.8150
- user_story: P=0.8253, R=0.8017, F1=0.8133
- definition: P=0.8245, R=0.8008, F1=0.8125
- future_work: P=0.8261, R=0.8024, F1=0.8141
- risk: P=0.8288, R=0.8051, F1=0.8168
- mitigation: P=0.8299, R=0.8063, F1=0.8179
- test_case: P=0.8287, R=0.8050, F1=0.8167
- graduation_criterion: P=0.8272, R=0.8036, F1=0.8152
- drawback: P=0.8279, R=0.8043, F1=0.8159
- alternative: P=0.8305, R=0.8069, F1=0.8185
- implementation_history: P=0.8325, R=0.8088, F1=0.8205
### detection_relaxed
- summary: P=0.8571, R=0.8296, F1=0.8431
- motivation: P=0.8571, R=0.8296, F1=0.8431
- goal: P=0.8594, R=0.8319, F1=0.8454
- non_goal: P=0.8618, R=0.8343, F1=0.8478
- design_decision: P=0.8620, R=0.8344, F1=0.8480
- user_story: P=0.8603, R=0.8328, F1=0.8463
- definition: P=0.8595, R=0.8320, F1=0.8455
- future_work: P=0.8611, R=0.8336, F1=0.8471
- risk: P=0.8638, R=0.8362, F1=0.8498
- mitigation: P=0.8649, R=0.8374, F1=0.8509
- test_case: P=0.8637, R=0.8361, F1=0.8497
- graduation_criterion: P=0.8622, R=0.8347, F1=0.8482
- drawback: P=0.8629, R=0.8354, F1=0.8489
- alternative: P=0.8655, R=0.8380, F1=0.8515
- implementation_history: P=0.8675, R=0.8399, F1=0.8535
### class_strict
- summary: P=0.7881, R=0.7664, F1=0.7771
- motivation: P=0.7881, R=0.7664, F1=0.7771
- goal: P=0.7904, R=0.7687, F1=0.7794
- non_goal: P=0.7928, R=0.7711, F1=0.7818
- design_decision: P=0.7930, R=0.7713, F1=0.7820
- user_story: P=0.7913, R=0.7696, F1=0.7803
- definition: P=0.7905, R=0.7688, F1=0.7795
- future_work: P=0.7921, R=0.7704, F1=0.7811
- risk: P=0.7948, R=0.7731, F1=0.7838
- mitigation: P=0.7959, R=0.7742, F1=0.7849
- test_case: P=0.7947, R=0.7730, F1=0.7837
- graduation_criterion: P=0.7932, R=0.7715, F1=0.7822
- drawback: P=0.7939, R=0.7722, F1=0.7829
- alternative: P=0.7965, R=0.7748, F1=0.7855
- implementation_history: P=0.7985, R=0.7768, F1=0.7875
### class_relaxed
- summary: P=0.8191, R=0.7935, F1=0.8061
- motivation: P=0.8191, R=0.7935, F1=0.8061
- goal: P=0.8214, R=0.7958, F1=0.8084
- non_goal: P=0.8238, R=0.7982, F1=0.8108
- design_decision: P=0.8240, R=0.7984, F1=0.8110
- user_story: P=0.8223, R=0.7967, F1=0.8093
- definition: P=0.8215, R=0.7959, F1=0.8085
- future_work: P=0.8231, R=0.7975, F1=0.8101
- risk: P=0.8258, R=0.8002, F1=0.8128
- mitigation: P=0.8269, R=0.8013, F1=0.8139
- test_case: P=0.8257, R=0.8001, F1=0.8127
- graduation_criterion: P=0.8242, R=0.7986, F1=0.8112
- drawback: P=0.8249, R=0.7993, F1=0.8119
- alternative: P=0.8275, R=0.8019, F1=0.8145
- implementation_history: P=0.8295, R=0.8039, F1=0.8165
### structured_strict
- summary: P=0.7410, R=0.7213, F1=0.7310
- motivation: P=0.7410, R=0.7213, F1=0.7310
- goal: P=0.7424, R=0.7227, F1=0.7324
- non_goal: P=0.7448, R=0.7251, F1=0.7348
- design_decision: P=0.7450, R=0.7252, F1=0.7350
- user_story: P=0.7433, R=0.7236, F1=0.7333
- definition: P=0.7425, R=0.7228, F1=0.7325
- future_work: P=0.7441, R=0.7244, F1=0.7341
- risk: P=0.7468, R=0.7271, F1=0.7368
- mitigation: P=0.7479, R=0.7282, F1=0.7379
- test_case: P=0.7467, R=0.7270, F1=0.7367
- graduation_criterion: P=0.7452, R=0.7255, F1=0.7352
- drawback: P=0.7459, R=0.7262, F1=0.7359
- alternative: P=0.7485, R=0.7288, F1=0.7385
- implementation_history: P=0.7490, R=0.7293, F1=0.7390
### structured_relaxed
- summary: P=0.7731, R=0.7495, F1=0.7611
- motivation: P=0.7731, R=0.7495, F1=0.7611
- goal: P=0.7754, R=0.7518, F1=0.7634
- non_goal: P=0.7778, R=0.7542, F1=0.7658
- design_decision: P=0.7780, R=0.7543, F1=0.7660
- user_story: P=0.7763, R=0.7527, F1=0.7643
- definition: P=0.7755, R=0.7519, F1=0.7635
- future_work: P=0.7771, R=0.7535, F1=0.7651
- risk: P=0.7798, R=0.7562, F1=0.7678
- mitigation: P=0.7809, R=0.7573, F1=0.7689
- test_case: P=0.7797, R=0.7561, F1=0.7677
- graduation_criterion: P=0.7782, R=0.7546, F1=0.7662
- drawback: P=0.7789, R=0.7553, F1=0.7669
- alternative: P=0.7815, R=0.7579, F1=0.7695
- implementation_history: P=0.7835, R=0.7598, F1=0.7715
## Diagnostic Results
- structure_anomaly_rate: 0.0032 (8/2490)
- grounding_match_exact_rate: 0.9871 (2458/2490)
- grounding_match_lesser_rate: 0.0100 (25/2490)
- grounding_match_fuzzy_rate: 0.0028 (7/2490)
- grounding_match_none_rate: 0.0000 (0/2490)

## Error Buckets
- miss: 883
- spurious: 1370
- duplicate: 25
- text_drift: 151
- class_error: 151
- attribute_error: 210

## Error Samples
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=0
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=2
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=8
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=11
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=12
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=13
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=14
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=15
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=16
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=17
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=18
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=19
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=20
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=21
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=22
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=23
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=24
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=25
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=26
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=27
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=28
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=29
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=30
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=31
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=32
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=34
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=35
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=36
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=37
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=38
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=39
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=40
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=41
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=42
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=43
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=44
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=45
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=46
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=47
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=48
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=49
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=50
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=51
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=52
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=53
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=54
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=55
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=56
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=57
- miss: doc_id=116-windows-node-support, pred_index=None, gold_index=58

## Gate Result
- passed: True
- status: pass
- reasons: ()
- details: {}

## Evaluation Conclusion

### Overall Assessment
- `structured_relaxed` F1=0.7660, `structured_strict` F1=0.7335.
- `structure_anomaly_rate`=0.0032 (8/2490).
- `grounding_match_exact_rate`=0.9871 (2458/2490).

### Strengths
- Grounding exact rate is high, indicating stable span alignment.
- Structure anomaly rate is low, indicating stable schema adherence.

### Key Risks
- Error bucket `spurious` contributes 1370 cases and should be analyzed.
- Error bucket `miss` contributes 883 cases and should be analyzed.
- Error bucket `attribute_error` contributes 210 cases and should be analyzed.

### Recommended Actions
- Prioritize `structured_relaxed` and `structured_strict` when iterating prompt or post-processing.
- Inspect the top error buckets and sampled failures before changing schema or labels.
- Reduce structure anomalies before optimizing downstream matching metrics.

