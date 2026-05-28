"""Structured service catalog for ZOSS service recommendation.

This module keeps the original public interface used by the current app:
- SERVICE_CATEGORIES
- SERVICE_HINTS
- SERVICE_OPTIONS
- RECOMMENDATION_RULES

Step 1 changes added in this version:
- category, price_min, price_max, price_note on every service
- slot_match for task-led slot-based recommendation
- hard_constraints for guardrail checks
- decision_profile for machine-readable service matching
- generated SERVICE_PRICE_BOUNDS / SERVICE_SLOT_MATCHES / SERVICE_HARD_CONSTRAINTS
"""

SERVICE_CATEGORIES = [   {   'title': '染髮',
        'subtitle': '服務皆含洗髮，不換色、不含漂、不提供孕婦染髮服務',
        'services': [   {   'name': '日本資生堂染髮',
                            'service_name': '日本資生堂染髮',
                            'price': '$1,799 / $2,099(指定)',
                            'description': '含頭皮隔離、水分子修護',
                            'keywords': ['想改變髮色', '染髮', '整體造型改變', '重視顏色表現與CP值'],
                            '適合對象': '適合想要改變整體髮色、嘗試自然色系或日常可接受髮色的顧客。若原本底色為黑髮、深棕髮，且目標是不漂髮也能完成的棕色、霧感深色、自然暖色或低調質感色，較適合選擇此服務。',
                            '不適合或限制': '不適合想要高明度淺色、灰白色、奶茶金、粉色、藍色、紫色等需要漂髮才能達到的特殊色。若髮色歷史複雜，例如曾染黑、染深、漂過或髮尾色塊不均，實際顯色可能受限制。',
                            '效果強項': '強項在於整體染髮的基本完成度、顏色表現與價格平衡，適合第一次染髮或想以合理預算改變造型的人。搭配頭皮隔離與水分子修護，可降低染髮過程中的頭皮不適與染後乾澀感。',
                            '代價或取捨': '不漂髮的情況下，顏色明亮度有限，最後成果會受到原本髮色影響。染後仍可能隨洗髮次數逐漸退色，需要使用護色洗髮精與降低高溫造型頻率來維持顏色。',
                            '與同類服務差異': '相較於日本哥德式染髮，資生堂染髮較適合重視CP值、想完成一般染髮需求、但不需要把修護放在第一優先的顧客。若顧客主要目標是改變髮色，而不是處理受損髮質，可優先推薦此服務。',
                            'category': '染髮',
                            'price_min': 1799,
                            'price_max': 2099,
                            'price_note': '指定設計師為 2099',
                            'slot_match': {   'direction': ['染髮'],
                                              'dye_detail': ['全頭染'],
                                              'target_color': ['自然深色', '一般棕色'],
                                              'current_base': ['自然黑髮', '已染深色/中深色'],
                                              'bleach_accept': ['希望不漂髮'],
                                              'brand_priority': ['重視顏色表現與CP值']},
                            'hard_constraints': {   'pregnant': 'not_allowed',
                                                    'onsite_evaluation_required': [   'complex_color_history',
                                                                                      'severe_damage']},
                            'decision_profile': {   'category': '染髮',
                                                    'price_min': 1799,
                                                    'price_max': 2099,
                                                    'price_note': '指定設計師為 2099',
                                                    'chemical_service': True,
                                                    'requires_onsite_evaluation': True,
                                                    'priority_fit': ['顏色表現與CP值', '自然換色', '預算平衡'],
                                                    'best_for': ['想整體改變髮色', '目標為自然色或一般棕色', '重視價格與效果平衡'],
                                                    'not_for': ['高明度特殊色', '需要漂髮才能完成的顏色', '髮色歷史複雜且期待精準顯色']}},
                        {   'name': '日本哥德式染髮',
                            'service_name': '日本哥德式染髮',
                            'price': '$2,299 / $2,599(指定)',
                            'description': '含頭皮隔離、水分子修護',
                            'keywords': ['重視染後髮質', '染後修護', '想染髮又在意髮質', '重視染後髮質修護'],
                            '適合對象': '適合想染髮但同時重視染後髮質、柔順度與整體質感的顧客。尤其適合髮尾偏乾、曾經染燙、容易毛躁、擔心染後變乾的人。',
                            '不適合或限制': '不適合期待不漂髮卻達到高明度特殊色的顧客。若髮況嚴重受損、髮尾彈性不足、斷裂明顯，仍需現場評估是否適合染髮，或先以護髮修復為優先。',
                            '效果強項': '強項在於染髮同時兼顧髮質修護感，染後觸感、柔順度與光澤通常會比一般染髮更被重視。適合對染後髮質有要求，或希望髮色看起來更有質感的人。',
                            '代價或取捨': '價格高於日本資生堂染髮，但換取較完整的染後質感與修護訴求。若顧客只想簡單補色或預算有限，可能不需要選到此等級。',
                            '與同類服務差異': '相較於日本資生堂染髮，哥德式染髮更適合把「染後髮質」放在第一優先的顧客。若顧客擔心染後乾燥、毛躁、質感下降，推薦哥德式會比資生堂更合理。',
                            'category': '染髮',
                            'price_min': 2299,
                            'price_max': 2599,
                            'price_note': '指定設計師為 2599',
                            'slot_match': {   'direction': ['染髮'],
                                              'dye_detail': ['全頭染'],
                                              'target_color': ['自然深色', '一般棕色'],
                                              'current_base': ['自然黑髮', '已染深色/中深色', '已染淺色/已漂過'],
                                              'bleach_accept': ['希望不漂髮'],
                                              'brand_priority': ['重視染後髮質修護', '兩者都重視']},
                            'hard_constraints': {   'pregnant': 'not_allowed',
                                                    'onsite_evaluation_required': [   'complex_color_history',
                                                                                      'severe_damage']},
                            'decision_profile': {   'category': '染髮',
                                                    'price_min': 2299,
                                                    'price_max': 2599,
                                                    'price_note': '指定設計師為 2599',
                                                    'chemical_service': True,
                                                    'requires_onsite_evaluation': True,
                                                    'priority_fit': ['染後髮質修護', '柔順度', '質感'],
                                                    'best_for': ['想染髮但在意染後髮質', '髮尾偏乾或容易毛躁', '希望染後質感更好'],
                                                    'not_for': ['期待不漂達成高明度特殊色', '髮況嚴重受損且不適合化學服務', '只需簡單補色且預算有限']}},
                        {   'name': '補染',
                            'service_name': '補染',
                            'price': '$1,099 / $1,399(指定)',
                            'description': '髮根3公分內',
                            'keywords': ['髮根補色', '補染', '只想補髮根'],
                            '適合對象': '適合原本已經染過頭髮，只是新生髮長出來、髮根與髮尾產生色差的顧客。目標是維持原本髮色的一致性，而不是大幅改變整體造型。',
                            '不適合或限制': '僅適用於髮根3公分內的補色需求。不適合整頭換色、髮尾退色嚴重、髮色不均、想改變髮色方向或想處理大面積色差的情況。',
                            '效果強項': '強項是快速處理髮根色差，讓整體髮色看起來更整齊乾淨。相較整頭染髮，補染時間、預算與對髮尾的化學負擔通常較低。',
                            '代價或取捨': '補染只能處理新生髮與原本髮色之間的銜接，無法改善髮尾退色、色塊不均或整體髮色老舊的問題。若原本髮色已退很多，補染後仍可能看得出髮尾與髮根差異。',
                            '與同類服務差異': '相較於整頭染髮，補染的目的不是重新設計髮色，而是維持既有髮色。若顧客只是髮根長出來，不需要整頭染；若顧客想換色或髮尾也退色，則應推薦染髮而不是補染。',
                            'category': '染髮',
                            'price_min': 1099,
                            'price_max': 1399,
                            'price_note': '髮根 3 公分內；指定設計師為 1399',
                            'slot_match': {'direction': ['染髮'], 'dye_detail': ['補染']},
                            'hard_constraints': {   'pregnant': 'not_allowed',
                                                    'onsite_evaluation_required': [   'complex_color_history',
                                                                                      'severe_damage'],
                                                    'dye_root_length_cm_max': 3},
                            'decision_profile': {   'category': '染髮',
                                                    'price_min': 1099,
                                                    'price_max': 1399,
                                                    'price_note': '髮根 3 公分內；指定設計師為 1399',
                                                    'chemical_service': True,
                                                    'requires_onsite_evaluation': True,
                                                    'priority_fit': ['髮根色差', '維持原髮色', '省時省預算'],
                                                    'best_for': ['新生髮根三公分內', '只想處理布丁頭', '維持原本髮色一致'],
                                                    'not_for': ['整頭換色', '髮尾退色嚴重', '超過髮根三公分的大面積色差']}},
                        {   'name': '漂髮',
                            'service_name': '漂髮',
                            'price': '$1,799 ~ $2,599',
                            'description': '以髮長計價',
                            'keywords': ['想漂髮', '特殊髮色', '淺色髮色'],
                            '適合對象': '適合想要明顯淺色、特殊色、灰色、奶茶色、粉色、藍色、紫色、透明感髮色，或希望髮色明度大幅提升的顧客。若目標色是不漂無法達成的顏色，就需要考慮漂髮。',
                            '不適合或限制': '不適合髮質嚴重受損、近期頻繁染燙、髮尾斷裂、彈性不足或無法接受退色與後續保養成本的顧客。曾染黑、染深或有複雜染髮歷史者，漂髮結果可能不均，需要現場評估。',
                            '效果強項': '強項是打開髮色明度，讓後續染色能呈現更明顯、更透明、更特殊的效果。若顧客追求高明度或特殊色，漂髮通常是必要前置步驟。',
                            '代價或取捨': '漂髮對髮質負擔較高，可能造成乾燥、毛躁、斷裂風險增加，也需要較高的後續護髮與護色成本。特殊色通常退色較快，維持期較短，可能需要定期補色。',
                            '與同類服務差異': '染髮是在既有底色上改變色調，漂髮則是先降低頭髮本身色素、提高明度。若顧客只是想要自然棕色或低調改變，不一定需要漂；若顧客想要淺色、灰感、霧感或特殊色，漂髮比一般染髮更符合目標。',
                            'category': '染髮',
                            'price_min': 1799,
                            'price_max': 2599,
                            'price_note': '以髮長計價',
                            'slot_match': {   'direction': ['染髮'],
                                              'dye_detail': ['漂髮設計染'],
                                              'target_color': ['高明度特殊色'],
                                              'bleach_accept': ['可接受漂髮']},
                            'hard_constraints': {   'pregnant': 'not_allowed',
                                                    'onsite_evaluation_required': [   'complex_color_history',
                                                                                      'severe_damage'],
                                                    'severe_damage': 'not_recommended_or_requires_onsite_evaluation'},
                            'decision_profile': {   'category': '染髮',
                                                    'price_min': 1799,
                                                    'price_max': 2599,
                                                    'price_note': '以髮長計價',
                                                    'chemical_service': True,
                                                    'requires_onsite_evaluation': True,
                                                    'priority_fit': ['高明度特殊色', '明顯變化', '特殊色前置'],
                                                    'best_for': ['想要高明度或特殊色', '願意承擔漂髮保養成本', '需要先提升髮色明度'],
                                                    'not_for': ['髮質嚴重受損', '無法接受退色與保養成本', '近期頻繁染燙']}}]},
    {   'title': '燙髮',
        'subtitle': '服務皆含洗髮，漂過頭髮的不可燙，不提供孕婦燙髮服務',
        'services': [   {   'name': '日本資生堂燙髮',
                            'service_name': '日本資生堂燙髮',
                            'price': '$1,799 / $2,099(指定)',
                            'description': '含水分子修護',
                            'keywords': ['想燙髮', '想改變捲度', '想整理造型'],
                            '適合對象': '適合想改變髮型線條、增加捲度、改善直髮單調感，或希望日常造型更有型的顧客。若髮況穩定、沒有漂髮紀錄，且主要目標是完成基本燙髮造型，可選擇此服務。',
                            '不適合或限制': '漂過的頭髮不可燙。不適合髮質嚴重受損、髮尾斷裂、彈性不足或近期多次染燙的顧客。若顧客髮質太細軟或受損，捲度持久度也可能受到影響。',
                            '效果強項': '強項在於以較平衡的預算完成捲度或線條改變，適合想要自然彎度、日常整理感、髮型變化的人。含水分子修護，可在燙髮過程中降低乾澀感。',
                            '代價或取捨': '燙髮後需要學習基本整理方式，例如吹整方向、使用造型品或避免過度拉直。若顧客不願意日常整理，實際效果可能不如預期。',
                            '與同類服務差異': '相較於日本哥德式燙髮，資生堂燙髮較適合髮況正常、預算較有限、主要想改變髮型的人。若顧客髮質偏乾或非常在意燙後修護感，哥德式燙髮會更適合。',
                            'category': '燙髮',
                            'price_min': 1799,
                            'price_max': 2099,
                            'price_note': '指定設計師為 2099',
                            'slot_match': {   'direction': ['燙髮'],
                                              'perm_detail': ['整體燙髮'],
                                              'perm_blocker': ['以上皆無'],
                                              'perm_preference': ['平衡預算，完成基本燙髮造型', '不確定']},
                            'hard_constraints': {   'pregnant': 'not_allowed',
                                                    'bleached_hair': 'not_allowed',
                                                    'severe_damage': 'not_allowed_or_requires_onsite_evaluation'},
                            'decision_profile': {   'category': '燙髮',
                                                    'price_min': 1799,
                                                    'price_max': 2099,
                                                    'price_note': '指定設計師為 2099',
                                                    'chemical_service': True,
                                                    'requires_onsite_evaluation': True,
                                                    'priority_fit': ['基本燙髮造型', '預算平衡', '改變捲度'],
                                                    'best_for': ['髮況穩定且未漂過', '主要想完成基本捲度或線條', '預算較保守'],
                                                    'not_for': ['曾經漂過頭髮', '目前懷孕', '髮質嚴重受損或容易斷裂']}},
                        {   'name': '日本哥德式燙髮',
                            'service_name': '日本哥德式燙髮',
                            'price': '$2,299 / $2,599(指定)',
                            'description': '含水分子修護',
                            'keywords': ['想燙髮又重視修護', '燙後髮質', '需要較完整燙髮修護'],
                            '適合對象': '適合想燙髮但同時重視髮質、彈性、柔順度與燙後觸感的顧客。尤其適合髮尾偏乾、曾染燙、容易毛躁，或擔心燙後髮質變差的人。',
                            '不適合或限制': '漂過的頭髮不可燙。若髮況已嚴重受損、斷裂明顯或髮尾失去彈性，即使選擇較重視修護的燙髮服務，也仍可能不適合操作。',
                            '效果強項': '強項是燙髮同時兼顧修護與質感，適合希望捲度自然、髮絲觸感不要過度乾澀的人。比起單純追求造型，這項服務更重視燙後髮質狀態。',
                            '代價或取捨': '價格高於日本資生堂燙髮，但換取較完整的修護與質感訴求。若顧客髮況很好、只是想做簡單捲度，可能不一定需要選到此服務。',
                            '與同類服務差異': '相較於日本資生堂燙髮，哥德式燙髮更適合把「燙後髮質」放在第一優先的顧客。若顧客擔心毛躁、乾燥或髮尾受損，推薦哥德式比資生堂更合理。',
                            'category': '燙髮',
                            'price_min': 2299,
                            'price_max': 2599,
                            'price_note': '指定設計師為 2599',
                            'slot_match': {   'direction': ['燙髮'],
                                              'perm_detail': ['整體燙髮'],
                                              'perm_blocker': ['以上皆無'],
                                              'perm_preference': ['重視燙後髮質、柔順度與修護感']},
                            'hard_constraints': {   'pregnant': 'not_allowed',
                                                    'bleached_hair': 'not_allowed',
                                                    'severe_damage': 'not_allowed_or_requires_onsite_evaluation'},
                            'decision_profile': {   'category': '燙髮',
                                                    'price_min': 2299,
                                                    'price_max': 2599,
                                                    'price_note': '指定設計師為 2599',
                                                    'chemical_service': True,
                                                    'requires_onsite_evaluation': True,
                                                    'priority_fit': ['燙後髮質修護', '柔順度', '質感'],
                                                    'best_for': ['髮況可燙但擔心燙後乾澀', '重視燙後柔順與質感', '願意提高預算換修護感'],
                                                    'not_for': ['曾經漂過頭髮', '目前懷孕', '髮質嚴重受損或容易斷裂']}},
                        {   'name': '髮根燙',
                            'service_name': '髮根燙',
                            'price': '$1,299 / $1,599(指定)',
                            'description': '適合想改善髮根扁塌的顧客',
                            'keywords': ['髮根扁塌', '頭頂塌', '想增加蓬鬆感', '蓬鬆'],
                            '適合對象': '適合頭頂容易扁塌、髮根貼頭皮、細軟髮、髮量視覺上不足，或希望頭型看起來更蓬鬆的顧客。目標是改善髮根支撐度，而不是改變整體捲度。',
                            '不適合或限制': '不適合想要整頭明顯捲度、髮尾彎度或大幅改變髮型的人。若頭皮敏感、髮根區域受損，或曾漂髮，需謹慎評估是否適合。',
                            '效果強項': '強項是改善頭頂扁塌與髮根貼頭皮問題，讓髮型看起來更有空氣感與精神感。對不想大幅改變髮型、只想改善輪廓的人特別適合。',
                            '代價或取捨': '效果主要集中在髮根，不會改變髮尾造型。髮根新生髮長出後，蓬鬆效果會逐漸下降，需要一段時間後重新施作。',
                            '與同類服務差異': '相較於一般燙髮，髮根燙不是為了製造捲度，而是為了增加頭頂支撐度。若顧客問題是「頭頂塌」，推薦髮根燙；若問題是「想要捲髮造型」，則應推薦一般燙髮。',
                            'category': '燙髮',
                            'price_min': 1299,
                            'price_max': 1599,
                            'price_note': '指定設計師為 1599',
                            'slot_match': {'direction': ['燙髮'], 'perm_detail': ['髮根燙'], 'perm_blocker': ['以上皆無']},
                            'hard_constraints': {   'pregnant': 'not_allowed',
                                                    'bleached_hair': 'not_allowed',
                                                    'severe_damage': 'not_allowed_or_requires_onsite_evaluation'},
                            'decision_profile': {   'category': '燙髮',
                                                    'price_min': 1299,
                                                    'price_max': 1599,
                                                    'price_note': '指定設計師為 1599',
                                                    'chemical_service': True,
                                                    'requires_onsite_evaluation': True,
                                                    'priority_fit': ['髮根蓬鬆', '頭頂扁塌', '局部改善'],
                                                    'best_for': ['頭頂扁塌', '髮根貼頭皮', '想增加髮根支撐度'],
                                                    'not_for': ['想要整頭明顯捲度', '曾經漂過頭髮', '頭皮或髮根狀況不穩定']}},
                        {   'name': '燙瀏海',
                            'service_name': '燙瀏海',
                            'price': '$999',
                            'description': '含修瀏海',
                            'keywords': ['瀏海', '瀏海整理', '燙瀏海'],
                            '適合對象': '適合瀏海容易亂翹、貼額頭、不順、不好整理，或想讓瀏海有自然弧度的顧客。也適合只想微調臉部周圍線條、不想整頭燙髮的人。',
                            '不適合或限制': '不適合想要整體髮型大幅改變、整頭捲度或髮根蓬鬆的人。若瀏海髮量太少、髮流太強、髮質受損或曾漂過，效果可能有限。',
                            '效果強項': '強項是快速改善瀏海線條與日常整理難度，讓瀏海更容易維持自然彎度。含修瀏海，可同時調整長度與形狀。',
                            '代價或取捨': '效果範圍只在瀏海，不會改善整體髮型。瀏海生長速度快，因此維持期通常比整頭燙髮短，需要較頻繁整理或修剪。',
                            '與同類服務差異': '相較於一般燙髮，燙瀏海是局部處理，適合只困擾於瀏海的人。若顧客只想讓瀏海順一點，不需要推薦整頭燙髮。',
                            'category': '燙髮',
                            'price_min': 999,
                            'price_max': 999,
                            'price_note': '含修瀏海',
                            'slot_match': {'direction': ['燙髮'], 'perm_detail': ['燙瀏海'], 'perm_blocker': ['以上皆無']},
                            'hard_constraints': {   'pregnant': 'not_allowed',
                                                    'bleached_hair': 'not_allowed',
                                                    'severe_damage': 'not_allowed_or_requires_onsite_evaluation'},
                            'decision_profile': {   'category': '燙髮',
                                                    'price_min': 999,
                                                    'price_max': 999,
                                                    'price_note': '含修瀏海',
                                                    'chemical_service': True,
                                                    'requires_onsite_evaluation': True,
                                                    'priority_fit': ['瀏海整理', '局部調整', '自然弧度'],
                                                    'best_for': ['瀏海亂翹或不好整理', '只想調整瀏海弧度', '不想整頭燙髮'],
                                                    'not_for': ['想整體大幅改變髮型', '曾經漂過頭髮', '瀏海髮量太少或髮質受損']}}]},
    {   'title': '護髮',
        'subtitle': '服務皆含洗髮',
        'services': [   {   'name': '哥德式護髮',
                            'service_name': '哥德式護髮',
                            'price': '$1,599',
                            'description': '適合染燙後受損、乾燥或髮尾毛裂，需要深層修護的顧客。',
                            'keywords': ['深層修護', '染燙受損', '髮尾乾燥', '髮尾毛裂'],
                            '適合對象': '適合染燙後受損、髮尾乾燥、毛裂、容易打結、摸起來粗硬，或頭髮缺乏彈性與光澤的顧客。若顧客近期有染髮或燙髮，並且想補強髮質，適合推薦此服務。',
                            '不適合或限制': '護髮無法修復已經完全斷裂或嚴重結構受損的頭髮，也無法讓受損髮恢復成完全未受損狀態。若髮尾分岔嚴重，仍可能需要修剪搭配護髮。',
                            '效果強項': '強項是深層修護、改善乾燥毛躁、提升髮絲柔順度與觸感，適合受損程度較明顯的人。比一般日常保養更偏向修護型。',
                            '代價或取捨': '價格高於一般基礎護髮，但修護訴求較完整。護髮效果會隨洗髮、熱工具與日常照護逐漸下降，需要定期保養才能維持。',
                            '與同類服務差異': '相較於哥德式可洛娜三劑式護髮與鉑金修護，哥德式護髮更適合受損較明顯、需要深層修護的人。若顧客是染燙後乾燥毛裂，應優先推薦此服務。',
                            'category': '護髮',
                            'price_min': 1599,
                            'price_max': 1599,
                            'price_note': '深層修護',
                            'slot_match': {'direction': ['護髮'], 'treatment_detail': ['受損修護']},
                            'hard_constraints': {},
                            'decision_profile': {   'category': '護髮',
                                                    'price_min': 1599,
                                                    'price_max': 1599,
                                                    'price_note': '深層修護',
                                                    'chemical_service': False,
                                                    'requires_onsite_evaluation': False,
                                                    'priority_fit': ['深層修護', '染燙受損', '乾燥毛裂'],
                                                    'best_for': ['染燙後受損', '髮尾乾燥毛裂', '需要深層修護'],
                                                    'not_for': ['期待修復已完全斷裂的頭髮', '只想改變髮色或捲度']}},
                        {   'name': '哥德式可洛娜三劑式護髮',
                            'service_name': '哥德式可洛娜三劑式護髮',
                            'price': '$1,099',
                            'description': '適合想提升柔順度、光澤與髮絲觸感的顧客。',
                            'keywords': ['柔順', '觸感', '毛躁', '打結'],
                            '適合對象': '適合頭髮容易毛躁、打結、摸起來不夠柔順，想改善髮絲觸感與光澤，但受損程度沒有到非常嚴重的顧客。',
                            '不適合或限制': '若顧客髮尾嚴重毛裂、染燙後高度受損或斷裂明顯，單靠此服務可能不夠，需要更深層的修護服務或搭配修剪。',
                            '效果強項': '強項是提升柔順度、改善打結、增加光澤與滑順觸感。適合想讓頭髮變得比較好梳、比較不毛躁的人。',
                            '代價或取捨': '修護深度低於哥德式護髮，但價格較低、適合一般毛躁與觸感改善。若顧客期待明顯修復嚴重受損髮，效果可能不如深層護髮。',
                            '與同類服務差異': '相較於哥德式護髮，可洛娜三劑式護髮較適合中度或輕中度毛躁、打結、觸感不佳的人；相較於鉑金修護，它更偏向改善柔順與觸感，而不只是日常保養。',
                            'category': '護髮',
                            'price_min': 1099,
                            'price_max': 1099,
                            'price_note': '三劑式護髮',
                            'slot_match': {'direction': ['護髮'], 'treatment_detail': ['柔順抗毛躁']},
                            'hard_constraints': {},
                            'decision_profile': {   'category': '護髮',
                                                    'price_min': 1099,
                                                    'price_max': 1099,
                                                    'price_note': '三劑式護髮',
                                                    'chemical_service': False,
                                                    'requires_onsite_evaluation': False,
                                                    'priority_fit': ['柔順抗毛躁', '觸感改善', '光澤'],
                                                    'best_for': ['頭髮毛躁打結', '想改善柔順與觸感', '受損程度不算嚴重'],
                                                    'not_for': ['嚴重染燙受損', '髮尾斷裂明顯', '期待深層修護效果']}},
                        {   'name': '鉑金修護',
                            'service_name': '鉑金修護',
                            'price': '$1,099',
                            'description': '適合日常保養、補充髮絲光澤與柔順感的顧客。',
                            'keywords': ['日常保養', '光澤', '入門護髮', '基礎修護'],
                            '適合對象': '適合髮況沒有嚴重受損，但想做日常保養、提升光澤、柔順感與整體質感的顧客。適合第一次做護髮、預算有限，或只是想維持髮況的人。',
                            '不適合或限制': '不適合嚴重染燙受損、髮尾毛裂、斷裂或高度乾燥的情況。若顧客已經有明顯受損問題，鉑金修護可能只能提供基礎保養感，修護力不足。',
                            '效果強項': '強項是作為入門護髮與日常保養，幫助頭髮看起來更有光澤、摸起來更柔順。適合沒有嚴重問題但想維持質感的人。',
                            '代價或取捨': '修護強度低於哥德式護髮，改善幅度較溫和。若顧客期待一次大幅改善受損髮質，應選擇更高修護等級的服務。',
                            '與同類服務差異': '相較於哥德式護髮，鉑金修護偏向基礎保養；相較於可洛娜三劑式護髮，它更適合日常維持與光澤補強。若顧客沒有嚴重受損，只是想讓頭髮更順更亮，可推薦鉑金修護。',
                            'category': '護髮',
                            'price_min': 1099,
                            'price_max': 1099,
                            'price_note': '日常保養',
                            'slot_match': {'direction': ['護髮'], 'treatment_detail': ['日常保養']},
                            'hard_constraints': {},
                            'decision_profile': {   'category': '護髮',
                                                    'price_min': 1099,
                                                    'price_max': 1099,
                                                    'price_note': '日常保養',
                                                    'chemical_service': False,
                                                    'requires_onsite_evaluation': False,
                                                    'priority_fit': ['日常保養', '基礎修護', '光澤維持'],
                                                    'best_for': ['日常保養', '髮況尚可但想維持光澤', '第一次做護髮或預算有限'],
                                                    'not_for': ['嚴重染燙受損', '髮尾毛裂斷裂', '期待大幅修復受損髮']}}]}]




def _service_name(service):
    return service.get("name") or service.get("service_name")


def iter_services():
    for category in SERVICE_CATEGORIES:
        for service in category.get("services", []):
            yield service


def get_service_by_name(service_name):
    for service in iter_services():
        if _service_name(service) == service_name:
            return service
    return None


def _service_profile(service):
    return {
        "適合對象": service.get("適合對象", ""),
        "不適合或限制": service.get("不適合或限制", ""),
        "效果強項": service.get("效果強項", ""),
        "代價或取捨": service.get("代價或取捨", ""),
        "與同類服務差異": service.get("與同類服務差異", ""),
    }


def _service_price_bounds():
    return {
        _service_name(service): {
            "min": int(service.get("price_min", 0)),
            "max": int(service.get("price_max", 999999)),
            "note": service.get("price_note", ""),
        }
        for service in iter_services()
        if _service_name(service)
    }


SERVICE_HINTS = {
    _service_name(service): {
        "reason": service.get("description", ""),
        "keywords": service.get("keywords", []),
        "category": service.get("category", ""),
        "price": service.get("price", ""),
        "price_min": service.get("price_min"),
        "price_max": service.get("price_max"),
        "price_note": service.get("price_note", ""),
        "slot_match": service.get("slot_match", {}),
        "hard_constraints": service.get("hard_constraints", {}),
        "decision_profile": service.get("decision_profile", {}),
        "profile": _service_profile(service),
    }
    for service in iter_services()
    if _service_name(service)
}

SERVICE_OPTIONS = {
    service_name: details["reason"]
    for service_name, details in SERVICE_HINTS.items()
}

SERVICE_PRICE_BOUNDS = _service_price_bounds()

SERVICE_SLOT_MATCHES = {
    service_name: details.get("slot_match", {})
    for service_name, details in SERVICE_HINTS.items()
}

SERVICE_HARD_CONSTRAINTS = {
    service_name: details.get("hard_constraints", {})
    for service_name, details in SERVICE_HINTS.items()
}

# Backward-compatible rules generated from each service's keywords.
# This avoids maintaining a separate keyword list that can drift away from SERVICE_CATEGORIES.
RECOMMENDATION_RULES = [
    (service_name, details.get("keywords", []))
    for service_name, details in SERVICE_HINTS.items()
]


# ---------------------------------------------------------------------------
# Task-led slot-based recommendation helper.
# This replaces index-based recommendation logic in hermes_client.py.
# ---------------------------------------------------------------------------

TASK_PERM_HARD_BLOCKERS = {"曾經漂過頭髮", "目前懷孕", "髮質嚴重受損或容易斷裂"}

BUDGET_RANGE_MAX = {
    "1200 以下": 1200,
    "1201-1800": 1800,
    "1801-2400": 2400,
    "2401 以上": 999999,
    "預算不確定": 999999,
}


def recommend_service_from_slots(slots):
    """Return final_output using service slot_match / hard_constraints.

    The returned recommended_service is always one legal SERVICE_OPTIONS key.
    """
    clean_slots = {key: value for key, value in dict(slots or {}).items() if value and value != "我不確定"}

    fallback = _safety_fallback_service(clean_slots)
    if fallback:
        return _build_final_output(
            fallback,
            clean_slots,
            prefix="你提供的條件中有不適合直接進行燙髮或化學處理的風險，因此先以較保守的護髮或保養方向作為參考。"
        )

    candidates = []
    for service in iter_services():
        name = _service_name(service)
        if not name:
            continue
        if not _service_matches_direction(service, clean_slots):
            continue
        if not _service_within_budget(service, clean_slots):
            continue
        score = _score_service(service, clean_slots)
        if score >= 0:
            candidates.append((score, -int(service.get("price_min", 999999)), name, service))

    if not candidates:
        service = _default_service_for_direction(clean_slots.get("direction"))
        return _build_final_output(service, clean_slots)

    candidates.sort(reverse=True)
    return _build_final_output(candidates[0][3], clean_slots)


def _score_service(service, slots):
    slot_match = service.get("slot_match", {}) or {}
    score = 0

    for slot, expected_values in slot_match.items():
        user_value = slots.get(slot)
        if not user_value:
            continue
        if user_value in expected_values:
            score += 3
        else:
            return -1

    # Reward general profile fit without requiring exact match.
    profile = service.get("decision_profile", {}) or {}
    priority_text = " ".join(profile.get("priority_fit", []) + profile.get("best_for", []))
    for value in slots.values():
        if isinstance(value, str) and value[:4] in priority_text:
            score += 1

    if slots.get("budget_range") in {"1200 以下", "1201-1800"}:
        score -= max(0, int(service.get("price_min", 0)) - BUDGET_RANGE_MAX[slots["budget_range"]]) // 500

    return score


def _service_matches_direction(service, slots):
    direction = slots.get("direction")
    if not direction:
        return True
    return service.get("category") == direction


def _service_within_budget(service, slots):
    budget = slots.get("budget_range")
    if not budget or budget == "預算不確定":
        return True
    max_budget = BUDGET_RANGE_MAX.get(budget)
    if not max_budget:
        return True
    # Do not discard all slightly-over services too aggressively; the reason will explain tradeoff.
    return int(service.get("price_min", 0)) <= max_budget + 300


def _safety_fallback_service(slots):
    if slots.get("direction") == "燙髮" and slots.get("perm_blocker") in TASK_PERM_HARD_BLOCKERS:
        if slots.get("perm_blocker") == "髮質嚴重受損或容易斷裂":
            return get_service_by_name("哥德式護髮") or _default_service_for_direction("護髮")
        return get_service_by_name("鉑金修護") or _default_service_for_direction("護髮")
    if slots.get("direction") == "染髮" and slots.get("target_color") == "高明度特殊色" and slots.get("bleach_accept") == "希望不漂髮":
        return get_service_by_name("日本哥德式染髮") or _default_service_for_direction("染髮")
    return None


def _default_service_for_direction(direction):
    preferred = {
        "染髮": "日本資生堂染髮",
        "燙髮": "日本資生堂燙髮",
        "護髮": "鉑金修護",
    }.get(direction)
    if preferred:
        service = get_service_by_name(preferred)
        if service:
            return service
    return next(iter_services())


def _build_final_output(service, slots, prefix=""):
    name = _service_name(service)
    description = service.get("description", "")
    profile = service.get("decision_profile", {}) or {}
    best_for = "、".join(profile.get("best_for", [])[:2])
    tradeoff = service.get("代價或取捨", "")
    chemical = bool(profile.get("chemical_service"))

    user_summary = _summarize_slots(slots)
    reason_parts = []
    if prefix:
        reason_parts.append(prefix)
    if user_summary:
        reason_parts.append(f"根據你提供的條件（{user_summary}），此服務與你的主要需求較一致。")
    if best_for:
        reason_parts.append(f"{name}適合{best_for}。")
    elif description:
        reason_parts.append(description)
    if tradeoff:
        reason_parts.append(tradeoff[:90])
    if chemical:
        reason_parts.append("實際可行性、藥劑選擇與髮況風險仍需以現場髮型師評估為準。")

    return {
        "recommended_service": name,
        "reason": "".join(reason_parts),
        "next_step": "可在左側服務卡片確認方案，並於現場讓設計師依實際髮況再次評估。",
    }


def _summarize_slots(slots):
    labels = []
    for key in (
        "direction",
        "dye_detail",
        "target_color",
        "current_base",
        "bleach_accept",
        "brand_priority",
        "perm_detail",
        "perm_blocker",
        "perm_preference",
        "treatment_detail",
        "budget_range",
    ):
        value = slots.get(key)
        if value and value != "我不確定":
            labels.append(value)
    return "、".join(labels)
