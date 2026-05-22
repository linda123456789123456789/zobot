# ZOSS Service Knowledge Base

本文件定義 ZOSS AI chatbot 可使用的服務項目、價格、適合情境、限制與推薦邏輯。

AI 最終推薦時，只能使用本文件列出的 service_name 或 approved_combination_name。
AI 不可自行創造服務名稱、價格或不存在的套餐。

---

# 1. ZOSS 品牌與服務特色

ZOSS 是高 CP 值平價美髮沙龍，主打染、燙、護不分長短均一價。
ZOSS 全程由設計師親自服務，不交給助理。
ZOSS 使用日本原廠資生堂、哥德式等沙龍產品。
ZOSS 價目表公開透明，不隨意亂加價。
ZOSS 分店位於北北基、桃園、台中、高雄等地。

AI 可在需要時簡短提及以上特色，但不要過度行銷。
主要任務仍是協助使用者選擇合適服務。

---

# 2. 價格與預約注意事項

## 2.1 價格標示

ZOSS 價目表分為：
- 不指定設計師價格
- 指定設計師價格

指定設計師的費用可能依設計師不同而有所差異，可能為 600 至 900 元，可至 ZOSS 官網價目表的頁面查詢。

## 2.2 付款方式

ZOSS 現場付款方式包含：
- 現金
- Line Pay

現場無提供刷卡機服務。

## 2.3 操作時間參考

- 剪髮、護髮、頭皮：約 1–1.5 小時
- 染髮：約 2.5–3 小時
- 漂髮：約 3–6 小時
- 燙髮：約 3–4 小時

實際時間會依髮質、髮長與服務內容有所不同。

## 2.4 重要限制

- 染燙髮需現場評估髮況。
- 若曾經不當染燙或使用 DIY 產品造成髮質太受損，可能無法操作。
- ZOSS 不提供孕婦染髮、燙髮服務。
- 漂過的頭髮屬於受損狀態，不可進行燙髮，可能造成嚴重斷裂與毛躁。
- 除修剪瀏海外，剪、染、燙、護、頭皮服務皆包含免費洗髮。
- ZOSS 不提供自備染膏及藥水服務。

---

# 3. 單項服務清單

## 3.1 剪髮

service_id: haircut  
service_name: 精緻剪髮  
category: 剪髮  
price_unassigned: 600  
price_assigned: 700 起  
includes: 洗髮  
estimated_time: 1–1.5 小時  
price_band: 低價位  

適合情境：
- 使用者想修整髮型。
- 使用者覺得頭髮太厚、太亂、沒有型。
- 使用者想改變輪廓，但不一定想染燙。
- 使用者想讓頭髮更好整理。
- 使用者預算較低，想先做基本改變。

不適合情境：
- 使用者主要想要明顯改變髮色。
- 使用者主要想改善嚴重毛躁或受損髮質，剪髮只能輔助，可能仍需護髮。
- 使用者期待捲度或燙直效果，剪髮無法達成。

推薦語氣範例：
如果你主要想讓整體看起來更清爽、比較好整理，但又不想做太大變化，可以優先考慮精緻剪髮。

---

## 3.2 修剪瀏海

service_id: bang_trim  
service_name: 修剪瀏海  
category: 剪髮  
price: 150  
includes: 不包含洗髮  
estimated_time: 短時間，依現場狀況  
price_band: 低價位  

適合情境：
- 使用者只有瀏海太長。
- 使用者想微調臉型修飾。
- 使用者預算很低，只想做小改變。

不適合情境：
- 使用者想整體換造型。
- 使用者想改善髮質、髮色或捲度。

---

## 3.3 護髮：哥德式新柔漾四劑護髮

service_id: treatment_goldtwell_four_step  
service_name: 哥德式新柔漾四劑護髮  
category: 護髮  
price: 1599  
includes: 洗髮  
estimated_time: 1–1.5 小時  
price_band: 中價位  

適合情境：
- 使用者在意髮質改善。
- 使用者有毛躁、乾燥、受損問題。
- 使用者不一定想改變髮色或髮型，但想讓頭髮質感變好。
- 使用者擔心染燙傷髮，想先做低風險改善。

不適合情境：
- 使用者期待明顯改變外觀。
- 使用者主要想換髮色或燙出捲度。

---

## 3.4 護髮：哥德式初芯潤澤五段護髮

service_id: treatment_goldtwell_five_step  
service_name: 哥德式初芯潤澤五段護髮  
category: 護髮  
price: 1599  
includes: 洗髮  
estimated_time: 1–1.5 小時  
price_band: 中價位  

適合情境：
- 使用者想加強潤澤感。
- 使用者覺得頭髮乾燥、缺乏光澤。
- 使用者想改善髮質但不想染燙。

不適合情境：
- 使用者主要想要明顯造型改變。
- 使用者想換髮色或燙髮。

---

## 3.5 護髮：哥德式可洛娜三劑式護髮

service_id: treatment_goldtwell_three_step  
service_name: 哥德式可洛娜三劑式護髮  
category: 護髮  
price: 1099  
includes: 洗髮  
estimated_time: 1–1.5 小時  
price_band: 中價位  

適合情境：
- 使用者想做基礎護髮。
- 使用者希望改善毛躁、乾燥。
- 使用者預算中等，想先改善髮質。

不適合情境：
- 使用者想做明顯外觀改變。
- 使用者主要想染髮或燙髮。

---

## 3.6 護髮：哥德式生技式護髮

service_id: treatment_goldtwell_biotech  
service_name: 哥德式生技式護髮  
category: 護髮  
price: 1099  
add_on_price_for_color_or_perm: 599  
includes: 洗髮  
estimated_time: 1–1.5 小時  
price_band: 中價位；染燙加購為低至中價位  

適合情境：
- 使用者想改善髮質。
- 使用者染燙時想搭配護髮，降低受損感。
- 使用者預算有限，但仍想加入基礎護髮。

不適合情境：
- 使用者完全不在意髮質，只想最低價格完成染燙。
- 使用者期待明顯改變髮色或捲度，護髮本身無法達成。

---

## 3.7 護髮：蕾娜塔鉑金修護髮膜

service_id: treatment_renata_platinum_mask  
service_name: 蕾娜塔鉑金修護髮膜  
category: 護髮  
price: 1099  
add_on_price_for_color_or_perm: 699  
includes: 洗髮  
estimated_time: 1–1.5 小時  
price_band: 中價位；染燙加購為低至中價位  

適合情境：
- 使用者想加強修護。
- 使用者擔心染燙後髮質變差。
- 使用者想在染髮或燙髮時搭配護髮。

不適合情境：
- 使用者只想換髮色或改變捲度，且完全不想加護髮預算。

---

## 3.8 頭皮護理

service_id: scalp_ome_aroma  
service_name: OME有機香氛紓壓  
category: 頭皮  
price: 1099  
includes: 洗髮  
estimated_time: 1–1.5 小時  
price_band: 中價位  

適合情境：
- 使用者想做頭皮保養。
- 使用者有頭皮出油、頭皮緊繃、想放鬆的需求。
- 使用者不想改變髮色或髮型，只想保養。

不適合情境：
- 使用者主要想換髮色。
- 使用者主要想燙髮、剪髮或改善髮尾受損。
- 使用者期待明顯外觀改變。

---

## 3.9 染髮：日本資生堂單色無漂髮

service_id: color_shiseido_single_no_bleach  
service_name: 日本資生堂單色染髮  
category: 染髮  
price_unassigned: 1799  
price_assigned: 2099  
includes: 頭皮隔離、水分子修護、洗髮  
does_not_include: 剪髮  
estimated_time: 2.5–3 小時  
price_band: 中價位  

適合情境：
- 使用者想改變髮色。
- 使用者想換氣質、顯白、看起來更有精神。
- 使用者想做自然、低調、單色染髮。
- 使用者不想漂髮，或擔心髮質受損。
- 使用者想要比剪髮更明顯的外觀變化。

不適合情境：
- 使用者想要高明度特殊色，可能需要漂髮。
- 使用者髮質嚴重受損，需現場評估。
- 使用者懷孕，不提供染髮服務。
- 使用者想自備染膏，ZOSS 不提供。

---

## 3.10 染髮：日本哥德式單色無漂髮

service_id: color_goldwell_single_no_bleach  
service_name: 日本哥德式單色染髮  
category: 染髮  
price_unassigned: 2299  
price_assigned: 2599  
includes: 頭皮隔離、水分子修護、洗髮  
does_not_include: 剪髮  
estimated_time: 2.5–3 小時  
price_band: 中至高價位  

適合情境：
- 使用者想改變髮色。
- 使用者想要更重視顯色度與光澤感。
- 使用者想做單色、無漂髮染髮。
- 使用者可以接受比資生堂染髮更高的預算。

不適合情境：
- 使用者預算較低。
- 使用者想要特殊高明度髮色，可能仍需漂髮。
- 使用者髮質嚴重受損或懷孕。

---

## 3.11 補染

service_id: pretouch_root_3cm  
service_name: 髮根3CM以內補染  
category: 補染  
price_unassigned: 1099  
price_assigned: 1399  
estimated_time: 依現場狀況，通常接近染髮服務  
price_band: 中價位  

適合情境：
- 使用者原本有染髮，髮根長出來。
- 使用者不想換色，只想補齊原本髮色。
- 使用者想維持原本髮色一致。

不適合情境：
- 使用者想換新髮色。
- 使用者髮根超過 3CM。
- 使用者期待特殊染髮效果。

限制說明：
補染不換色，依照原髮色由設計師調配染膏。

---

## 3.12 漂髮

service_id: bleach  
service_name: 漂髮  
category: 漂髮  
price_short_unassigned: 1799  
price_short_assigned: 2099  
price_long_unassigned: 2299  
price_long_assigned: 2599  
pricing_note: 以次數計價，總額需現場溝通討論  
includes: 頭皮隔離、水分子修護、洗髮  
does_not_include: 剪髮  
estimated_time: 3–6 小時  
price_band: 高價位  

適合情境：
- 使用者想做高明度髮色。
- 使用者想做特殊色，例如灰色、粉色、藍色、紫色、奶茶色等可能需要漂的髮色。
- 使用者可以接受較高預算、較長時間與較高維護成本。
- 使用者願意接受現場評估。

不適合情境：
- 使用者非常擔心傷髮質。
- 使用者想要低維護、低風險。
- 使用者不想花太久時間。
- 使用者髮質已嚴重受損。
- 使用者之後想燙髮，因漂過頭髮不可進行燙髮。

限制說明：
漂髮以次數計價。
接漂或補漂屬於特殊項目，費用另計，需現場評估諮詢。

---

## 3.13 燙髮：資生堂水質感

service_id: perm_shiseido  
service_name: 資生堂水質感燙髮  
category: 燙髮  
price_unassigned: 1799  
price_assigned: 2099  
includes: 水分子修護、洗髮  
does_not_include: 剪髮  
estimated_time: 3–4 小時  
price_band: 中價位  

適合情境：
- 使用者想改變頭髮形狀。
- 使用者想要捲度、蓬鬆感、修飾臉型。
- 使用者想讓頭髮比較有造型。
- 使用者想做燙直或捲髮。
- 使用者想改善日常整理方式。

不適合情境：
- 使用者漂過頭髮。
- 使用者髮質嚴重受損。
- 使用者懷孕，不提供燙髮服務。
- 使用者只想改變髮色。
- 使用者想要上直下捲但不能接受加價。

備註：
直或捲皆可操作。
若選擇上直下捲需加價 999 元。

---

## 3.14 燙髮：哥德式水鑽光

service_id: perm_goldwell  
service_name: 哥德式水鑽光燙髮  
category: 燙髮  
price_unassigned: 2299  
price_assigned: 2599  
includes: 水分子修護、洗髮  
does_not_include: 剪髮  
estimated_time: 3–4 小時  
price_band: 中至高價位  

適合情境：
- 使用者想燙髮並願意接受較高預算。
- 使用者重視燙後質感、光澤或更好的藥水選項。
- 使用者想要捲度、蓬鬆度、燙直或造型感。

不適合情境：
- 使用者漂過頭髮。
- 使用者髮質嚴重受損。
- 使用者懷孕。
- 使用者預算較低。

備註：
直或捲皆可操作。
若選擇上直下捲需加價 999 元。

---

## 3.15 髮根澎澎燙

service_id: root_volume_perm  
service_name: 髮根澎澎燙  
category: 燙髮  
price_unassigned: 1299  
price_assigned: 1599  
includes: 不含剪髮  
estimated_time: 依現場狀況  
price_band: 中價位  

適合情境：
- 使用者頭頂容易扁塌。
- 使用者想增加髮根蓬鬆度。
- 使用者不一定想做整頭燙髮。
- 使用者想讓頭髮看起來比較有精神。

不適合情境：
- 使用者想改變整體捲度。
- 使用者想燙直。
- 使用者漂過頭髮或髮質嚴重受損，需謹慎評估。

---

## 3.16 燙瀏海

service_id: bang_perm  
service_name: 燙瀏海  
category: 燙髮  
price: 999  
includes: 修剪瀏海  
estimated_time: 依現場狀況  
price_band: 低至中價位  

適合情境：
- 使用者只想整理瀏海弧度。
- 使用者瀏海容易亂翹。
- 使用者想微調前額造型，不想整頭燙髮。

不適合情境：
- 使用者想整體換髮型。
- 使用者想改變髮色。
- 使用者沒有瀏海或不想調整瀏海。

---

## 3.17 局部燙

service_id: partial_perm_addon  
service_name: 局部燙  
category: 燙髮  
price: 999  
pricing_note: 兩種燙工加購價  
estimated_time: 依現場狀況  
price_band: 低至中價位  

適合情境：
- 使用者只想調整局部線條。
- 使用者需要搭配其他燙髮服務。
- 使用者不想整頭大幅改變。

不適合情境：
- 使用者想做完整燙髮效果。
- 使用者期待單靠局部燙大幅改變造型。

---

## 3.18 特殊染髮 / 燙髮

service_id: special_color_or_perm  
service_name: 特殊染髮 / 燙髮  
category: 其它  
price: 現場諮詢  
estimated_time: 依現場評估  
price_band: 高價位或不確定  

適合情境：
- 使用者想做特殊色、挑染、局部挑漂、複雜設計染。
- 使用者想做非一般單色染髮。
- 使用者需求無法用一般染髮或燙髮涵蓋。

不適合情境：
- 使用者需要立即知道精準價格。
- 使用者不願意現場諮詢。
- 使用者預算非常固定且無法接受變動。

限制說明：
特殊染髮或燙髮需現場諮詢。
AI 不可直接承諾可操作或給出固定價格。

---

# 4. 核准組合服務清單（approved combinations）

以下為可用的組合服務名稱與代碼。  
AI 若推薦組合方案，必須使用以下 `approved_combination_name` 與 `approved_combination_id`，不可自行創造。

## 4.1 剪髮＋染髮

approved_combination_id: combo_haircut_plus_color  
approved_combination_name: 剪髮＋染髮  
components:
- haircut
- color_shiseido_single_no_bleach 或 color_goldwell_single_no_bleach
price_band: 高價位  
pricing_note: 實際金額依選擇的染髮品牌與是否指定設計師而定。  

限制說明：
- 若使用者懷孕，不可推薦此組合。
- 若髮質嚴重受損，需現場評估。

---

## 4.2 剪髮＋燙髮

approved_combination_id: combo_haircut_plus_perm  
approved_combination_name: 剪髮＋燙髮  
components:
- haircut
- perm_shiseido 或 perm_goldwell
price_band: 高價位  
pricing_note: 實際金額依燙髮品牌與是否指定設計師而定。  

限制說明：
- 若使用者曾漂髮，不可推薦此組合。
- 若使用者懷孕，不可推薦此組合。
- 若髮質嚴重受損，需現場評估。

---

## 4.3 染髮＋護髮

approved_combination_id: combo_color_plus_treatment  
approved_combination_name: 染髮＋護髮  
components:
- color_shiseido_single_no_bleach 或 color_goldwell_single_no_bleach
- treatment_goldtwell_four_step 或 treatment_goldtwell_five_step 或 treatment_goldtwell_three_step 或 treatment_goldtwell_biotech 或 treatment_renata_platinum_mask
price_band: 高價位  
pricing_note: 實際金額依染髮品牌、護髮品項與是否指定設計師而定。  

限制說明：
- 若使用者懷孕，不可推薦此組合。
- 若髮質狀態不適合染髮，需現場評估。

---

## 4.4 燙髮＋護髮

approved_combination_id: combo_perm_plus_treatment  
approved_combination_name: 燙髮＋護髮  
components:
- perm_shiseido 或 perm_goldwell
- treatment_goldtwell_four_step 或 treatment_goldtwell_five_step 或 treatment_goldtwell_three_step 或 treatment_goldtwell_biotech 或 treatment_renata_platinum_mask
price_band: 高價位  
pricing_note: 實際金額依燙髮品牌、護髮品項與是否指定設計師而定。  

限制說明：
- 若使用者曾漂髮，不可推薦此組合。
- 若使用者懷孕，不可推薦此組合。
- 若髮質嚴重受損，需現場評估。

---

## 4.5 剪髮＋護髮

approved_combination_id: combo_haircut_plus_treatment  
approved_combination_name: 剪髮＋護髮  
components:
- haircut
- treatment_goldtwell_four_step 或 treatment_goldtwell_five_step 或 treatment_goldtwell_three_step 或 treatment_goldtwell_biotech 或 treatment_renata_platinum_mask
price_band: 中至高價位  
pricing_note: 實際金額依護髮品項與是否指定設計師而定。  

---

## 4.6 漂髮＋染髮

approved_combination_id: combo_bleach_plus_color  
approved_combination_name: 漂髮＋染髮  
components:
- bleach
- color_shiseido_single_no_bleach 或 color_goldwell_single_no_bleach
price_band: 高價位  
pricing_note: 漂髮以次數計價，總額需依髮長、目標色與現場評估確認。  

限制說明：
- 必須標示為需現場評估。
- 若使用者非常擔心受損，不優先推薦。
- 涉及特殊色、接漂、補漂時，需現場諮詢。

---

## 4.7 染髮＋漂髮＋護髮

approved_combination_id: combo_color_plus_bleach_plus_treatment  
approved_combination_name: 染髮＋漂髮＋護髮  
components:
- bleach
- color_shiseido_single_no_bleach 或 color_goldwell_single_no_bleach
- treatment_goldtwell_four_step 或 treatment_goldtwell_five_step 或 treatment_goldtwell_three_step 或 treatment_goldtwell_biotech 或 treatment_renata_platinum_mask
price_band: 高價位  
pricing_note: 漂髮次數、目標色、護髮品項與設計師指定會影響總價，需現場評估。  

限制說明：
- 必須標示為需現場評估或需現場諮詢。
- 若使用者髮質嚴重受損，可能無法操作。

---

# 5. 對話按鈕欄位映射（共用）

以下欄位可作為 button 條件下的共用題軸。  
task-led 與 topic-led 皆可使用同一組題軸，僅回覆語氣不同。
每輪實際出題時，請從同一題軸中選出 2 個互斥選項，並固定加上「不確定 / 想看建議」作為第 3 個按鈕。

1. 變化方向
- 想換髮色
- 想改變髮型線條 / 捲度
- 想先改善髮質 / 頭皮

2. 變化程度
- 自然低調
- 明顯變化
- 不確定，想看建議

3. 髮質風險偏好
- 優先低受損
- 可接受較高變化與保養成本
- 不確定，想先評估

4. 預算帶
- 低價位
- 中價位
- 高價位

5. 時間帶
- 1 至 1.5 小時
- 2.5 至 3 小時
- 3 小時以上
