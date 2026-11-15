# 13 · Related work

**Use:** reference. It is the source for the report's related-work section and the bibliography.
**Read by:** EVAL (report editor); everyone before the presentation.
**Checked:** 2026-11-09.

**Citation status:**

- Entries with a link were confirmed on the paper's own page, DOI record or arXiv record that day.
- *(meta)* means only the title, authors, venue and year were confirmed; the summary comes from the abstract.
- *(unverified)* means search snippets or secondary sources only. Do not cite these in the report until someone has opened the paper.

## 1. Positioning

FoodSwap is a **natural-language, compound critique on a reference product** ("like this, but less sugar and no peanuts"). It is evaluated as an IR system over branded packaged foods. Compared with prior work:

- **Critiquing recommenders** (FindMe, compound critiquing) introduced "like this but cheaper". FoodSwap applies the idea to free-text requests and hybrid retrieval.
- **Food substitution research** is almost entirely about recipe ingredients. The closest work on packaged products is Hafez et al. (2021) and Loesch et al. (2024). Neither parses a free-text request or guarantees hard constraints.
- **Neural retrievers fail on negation and numeric conditions** (NevIR, ExcluIR, NumConQ). FoodSwap therefore separates hard constraints and enforces them symbolically.
- **Allergen data is unreliable,** and precautionary labels are inconsistent. FoodSwap abstains when evidence is missing, as Open Food Facts' own `unknown_match` status does, and reports the cost.
- **Healthier-swap trials show most swaps are declined,** and effective systems stayed within the same category. FoodSwap scores similarity to the reference explicitly instead of assuming it.
- **Existing apps** (Yuka, FoodSwitch, the NHS Food Scanner, hundreds of student projects on Open Food Facts) choose "same category, better score". That becomes our baseline X2.
- **Generated explanations can be unfaithful,** so FoodSwap uses data-grounded templates, including why-not explanations.

## 2. Food and ingredient substitution

| Work | What it does | What we take |
|---|---|---|
| Loesch, Meeckers, van Lier, de Boer, Dumontier, Celebi. "Automated Identification of Food Substitutions Using Knowledge Graph Embeddings." SWAT4HCLS 2022, [CEUR Vol-3127](https://ceur-ws.org/Vol-3127/) *(meta)* | Knowledge-graph embeddings over food knowledge graphs; expert-validated pairs | Already cited in the proposal |
| Loesch et al. "Automated identification of healthier food substitutions through a combination of graph neural networks and nutri-scores." *J. Food Composition and Analysis* 125:105829 (2024). [doi](https://doi.org/10.1016/j.jfca.2023.105829) | GNN candidates from the same category, then ranked by Nutri-Score. Recall@5 0.647. The authors note that the same-category restriction misses less closely related substitutes. | **Closest academic precedent**: similarity first, then a nutrition ranking. FoodSwap adds hard constraints, free-text goals and grounded explanations. |
| Hafez, Díaz Redondo, Fernández-Vilas, Olivera Pazó. "Multi-criteria recommendation systems to foster online grocery." *Sensors* 21(11):3747 (2021). [arXiv 2312.08393](https://arxiv.org/abs/2312.08393) | Branded grocery recommendations from composition, packaging, nutrition and allergens, evaluated by user and expert surveys. Drops products with missing nutrient values. | The closest work on packaged products; no constraint guarantee and no query parsing |
| Shirai, Seneviratne, Gordon, Chen, McGuinness. "Identifying Ingredient Substitutions Using a Knowledge Graph of Food." *Frontiers in AI* (2021). [doi](https://doi.org/10.3389/frai.2020.621766) *(meta)* | DIISH: FoodKG combined with embeddings, with health filtering as a separate step | Explicit features combined with dense similarity |
| Pellegrini, Özsoy, Wintergerst, Groh. "Exploiting Food Embeddings for Ingredient Substitution." HEALTHINF 2021. [doi](https://doi.org/10.5220/0010202000670077) | Food2Vec and FoodBERT; evaluated with ground truth and human judges | Use both automatic and human evaluation |
| Fatemi, Duval, Girdhar, Drozdzal, Romero-Soriano. "Learning to Substitute Ingredients in Recipes." [arXiv 2302.07960](https://arxiv.org/abs/2302.07960) (2023) | GISMo and the Recipe1MSubs benchmark (MRR, Hit@k) | Ranking metrics on substitution pairs |
| Achananuparp and Weber. "Extracting Food Substitutes From Food Diary via Distributional Similarity." [arXiv 1607.08807](https://arxiv.org/abs/1607.08807) (2016) | Substitutes mined from MyFitnessPal diaries, validated by the crowd | Human substitutability judgments are a valid ground truth |
| Teng, Lin, Adamic. "Recipe recommendation using ingredient networks." WebSci 2012. [doi](https://doi.org/10.1145/2380718.2380757) | Substitution networks from recipe edits; users tend to substitute toward healthier variants | Background |
| Kim, Venkataramanan, Sheth. "A Survey on Food Ingredient Substitutions." [arXiv 2501.01958](https://arxiv.org/abs/2501.01958) | Survey of datasets and methods, plus safety, transparency and trust | The overview to cite |
| Senath et al. "LLMs for ingredient substitution with SFT and DPO." [arXiv 2412.04922](https://arxiv.org/abs/2412.04922) (2024) | A fine-tuned 7B model reaches Hit@1 of 22% on Recipe1MSubs | Even tuned LLMs are weak at this task, which supports keeping LLMs out of eligibility decisions |
| Chan and Tagkopoulos. "Translating Dietary Standards into Healthy Meals with Minimal Substitutions." [arXiv 2602.13502](https://arxiv.org/abs/2602.13502) (2026) | One to three swaps make meals about 10% more nutritious | Supports the "minimal change" framing |

## 3. Substitute recommendation in e-commerce and grocery

- **McAuley, Pandey, Leskovec.** "Inferring Networks of Substitutable and Complementary Products." KDD 2015. [doi](https://doi.org/10.1145/2783258.2783381) *(meta)*. The canonical definition of substitutes and complements, learned from co-view and co-purchase behaviour. FoodSwap derives substitutes from content and constraints instead.
- **Wang et al.** "A Path-constrained Framework for Discriminating Substitutable and Complementary Products." WSDM 2018. [doi](https://doi.org/10.1145/3159652.3159710) *(meta)*.
- **Rakesh et al.** "Linked Variational AutoEncoders for Inferring Substitutable and Supplementary Items." WSDM 2019. [doi](https://doi.org/10.1145/3289600.3290963) *(meta)*.
- **Liu et al.** "Decoupled Graph Convolution Network for Inferring Substitutable and Complementary Items." CIKM 2020. [doi](https://doi.org/10.1145/3340531.3412695) *(meta)*.
- **Chen et al.** "Try This Instead: Personalized and Interpretable Substitute Recommendation." SIGIR 2020. [doi](https://doi.org/10.1145/3397271.3401042) *(meta)*. Attribute-level explanations for substitutes ("cheaper, higher protein"), which our templates echo.
- **Reddy et al.** "Shopping Queries Dataset: A Large-Scale ESCI Benchmark for Improving Product Search." [arXiv 2206.06588](https://arxiv.org/abs/2206.06588) (2022).
  - Size: about 130K queries and 2.6M human judgments.
  - Labels: Exact; Substitute ("fails to fulfill some aspects of the query but … can be used as a functional substitute"); Complement; Irrelevant. The KDD Cup 2022 gains were 1.0 / 0.1 / 0.01 / 0.
  - It samples negation queries such as "energy bar without nuts" as a hard subset.
  - Our rubric borrows its structure. For FoodSwap, though, a substitute is the target, not a consolation prize.
- **Industry practice.** Instacart describes a model that predicts whether a customer will accept an out-of-stock replacement *(unverified; the blog returned 403)*. A retail study reports that matching on the dominant attribute raised replacement acceptance from 66% to 75% *(unverified)*.
- **Product search at TREC.** The TREC 2023 Product Search overview (Campos et al., [arXiv 2311.07861](https://arxiv.org/abs/2311.07861)) found traditional lexical systems highly effective and often better than single-stage dense retrieval.
- **Query understanding.** QueryNER (LREC-COLING 2024) and WANDS (Wayfair, ECIR 2022) *(meta / unverified)* are useful background on query understanding and product-search test collections.

## 4. Critiquing, knowledge-based and constraint-based recommenders

- **Burke, Hammond, Young.** "The FindMe approach to assisted browsing." *IEEE Expert* 12(4) (1997). [doi](https://doi.org/10.1109/64.608186) *(meta)*. Entree's "like this, but cheaper" tweaks are the direct ancestor of "like this cereal, but less sugar".
- **Burke.** "Hybrid Recommender Systems: Survey and Experiments." *UMUAI* 12 (2002). [doi](https://doi.org/10.1023/A:1021240730564). Already cited in the proposal.
- **Chen and Pu.** "Critiquing-based recommenders: survey and emerging trends." *UMUAI* 22 (2012). [doi](https://doi.org/10.1007/s11257-011-9108-6) *(meta)*. Its taxonomy places FoodSwap as a natural-language, user-initiated, compound critique.
- **Felfernig and Burke.** "Constraint-based recommender systems: technologies and research issues." ICEC 2008. [doi](https://doi.org/10.1145/1409540.1409544) *(meta)*.
- **Query relaxation for over-constrained requests:** McSherry (ECCBR 2004), Mirzadeh, Ricci and Bansal (EC-Web 2004), Jannach (*AI Communications* 2009) *(all unverified)*. What we take: when nothing is eligible, relax soft preferences, never hard ones, and say what was relaxed (F-C14).
- **Language-based critiquing:**
  - Wu et al., "Deep language-based critiquing," RecSys 2019. [doi](https://doi.org/10.1145/3298689.3347009) *(meta)*.
  - Luo et al., "Latent Linear Critiquing," WWW 2020. [doi](https://doi.org/10.1145/3366423.3380003) *(meta)*.
  - REGEN, a 2025 dataset of natural-language critiques. [arXiv 2503.11924](https://arxiv.org/abs/2503.11924).

## 5. Constraints and negation in retrieval

| Work | Finding |
|---|---|
| Weller, Lawrie, Van Durme. "NevIR: Negation in Neural Information Retrieval." EACL 2024. [ACL Anthology](https://aclanthology.org/2024.eacl-long.139/) | On pairs that differ only by negation, most neural retrievers score at or below random; cross-encoders do best. Cited in the proposal. |
| A reproducibility study of NevIR, SIGIR 2025. [arXiv 2502.13506](https://arxiv.org/abs/2502.13506) *(from search results)* | Listwise LLM rerankers do best but stay below humans; fine-tuning on one negation benchmark does not transfer to another |
| Zhang et al. "ExcluIR." [arXiv 2404.17288](https://arxiv.org/abs/2404.17288) (AAAI 2025 *(venue unverified)*) | 3,452 exclusionary queries; retrievers struggle |
| Zhang et al. "BoolQuestions." Findings of EMNLP 2024. [arXiv 2411.12235](https://arxiv.org/abs/2411.12235) | Large drops on NOT queries, even for LLM-based retrievers |
| Malaviya et al. "QUEST." ACL 2023. [ACL Anthology](https://aclanthology.org/2023.acl-long.784/) | Queries with negation and conjunction are particularly hard |
| Wang, Wang, Wu. "Numerical Constraint-Aware Dense Retrieval" (NumConQ). *Big Data Mining and Analytics* (2025/2026). [doi](https://doi.org/10.26599/BDMA.2025.9020047) | Dense retrievers satisfy numeric constraints only about 16.3% of the time |
| Weller et al. "FollowIR." [arXiv 2403.15246](https://arxiv.org/abs/2403.15246); "Promptriever." [arXiv 2409.11136](https://arxiv.org/abs/2409.11136) | Retrievers mostly ignore instructions; instruction-trained retrievers improve |
| Petcu et al. "A Comprehensive Taxonomy of Negation for NLP and Neural Retrievers." [arXiv 2507.22337](https://arxiv.org/abs/2507.22337) (2025) | Taxonomy of negation types |
| Yin, Tang, Du. "CoDeR." [arXiv 2606.13204](https://arxiv.org/abs/2606.13204) (2026) | Separates topical relevance from a learned constraint-compatibility score; fewer violations on negation diagnostics |

**Consequence for FoodSwap:** exclusions and numeric limits are parsed and enforced symbolically, and the negation experiment (RQ1) measures what happens when they are not.

## 6. Health-aware food recommendation and healthier-swap trials

**Recommender systems:**

- **Trattner and Elsweiler.** "Food Recommender Systems: Important Contributions, Challenges and Future Research Directions." [arXiv 1711.02760](https://arxiv.org/abs/1711.02760) (2017).
- **Trattner and Elsweiler.** "Investigating the Healthiness of Internet-Sourced Recipes." WWW 2017. [doi](https://doi.org/10.1145/3038912.3052573) *(meta)*. Popular recipes are unhealthy, and recommenders reproduce that.
- **Elsweiler, Trattner, Harvey.** "Exploiting Food Choice Biases for Healthier Recipe Recommendation." SIGIR 2017. [doi](https://doi.org/10.1145/3077136.3080826) *(meta)*. Replaces a recipe with a similar, healthier one. The closest IR precedent for "similar but better".
- **Bondevik et al.** "A systematic review on food recommender systems." *Expert Systems with Applications* 238 (2024). [doi](https://doi.org/10.1016/j.eswa.2023.122166). 67 studies; mostly content-based; offline accuracy metrics dominate.
- **Starke, Willemsen, Trattner** (*Frontiers in AI* 2021) and **Starke, El Majjodi, Trattner** ([IntRS'22](https://dars.uib.no/pubs/IntRS_22.pdf)). Ranking healthy items first and showing traffic-light labels shift choices without hurting satisfaction. Users were less satisfied with constraint-based preference elicitation, which is one reason to keep FoodSwap's interaction to a single sentence.

**Randomized trials of healthier swaps:**

| Trial | Result |
|---|---|
| Forwood, Ahern, Marteau, Jebb. *IJBNPA* 12:85 (2015). [doi](https://doi.org/10.1186/s12966-015-0241-1) | Online shop, n = 1,610. Swaps were limited to the same category and similar size and price. 47% accepted no swap. Swaps with larger energy reductions were accepted less often. |
| Koutoukidis et al. *IJBNPA* (2019). [doi](https://doi.org/10.1186/s12966-019-0810-9) *(meta)* | Reordering products cut basket saturated fat more than offering swaps did |
| Payne Riches et al. *Appetite* 133 (2019). [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6335438) | "Much lower salt" swaps were accepted as often as "lower salt" swaps |
| Eyles et al. SaltSwitch RCT. *Eur J Prev Cardiol* 24(13) (2017). [doi](https://doi.org/10.1177/2047487317715713) | App-based swaps reduced purchased salt |
| Jansen, van Kleef, Van Loo. *IJBNPA* 18:156 (2021). [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8642761/) | Same-category swap offers improved nutrient-profile scores far more than Nutri-Score labels alone |
| Schruff-Lim et al. *Appetite* 194 (2024). [doi](https://doi.org/10.1016/j.appet.2023.107158) *(meta)* | Swaps beat labels alone; similar vs. dissimilar swaps made little difference |
| Grummon et al. *PLOS Medicine* (Aug 2026). [journal](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.1004847) | US adults, n = 1,201. About 25–27% of offered swaps were accepted. |

**What we take:**

- Most swaps are declined.
- The effect of similarity on acceptance is mixed across studies.
- Every effective system kept swaps inside the same category.
- FoodSwap therefore scores similarity explicitly (β·C) and measures it, rather than assuming it.

## 7. Explanations

- **Tintarev and Masthoff.** "A Survey of Explanations in Recommender Systems" (ICDE Workshops 2007, [doi](https://doi.org/10.1109/ICDEW.2007.4401070)) and "Explaining Recommendations: Design and Evaluation" (*Recommender Systems Handbook*, 2015, [doi](https://doi.org/10.1007/978-1-4899-7637-6_10)) *(meta)*. They define seven aims of explanations; FoodSwap targets transparency, scrutability and effectiveness, not persuasion.
- **Herlocker, Konstan, Riedl.** "Explaining collaborative filtering recommendations." CSCW 2000. [doi](https://doi.org/10.1145/358916.358995) *(meta)*.
- **Bilgic and Mooney.** "Explaining Recommendations: Satisfaction vs. Promotion." IUI 2005 workshop *(unverified)*. Explanations should help users estimate quality accurately, not oversell.
- **Zhang and Chen.** "Explainable Recommendation: A Survey and New Perspectives." *FnTIR* (2020). [doi](https://doi.org/10.1561/1500000066) *(meta)*.
- **Balog and Radlinski.** "Measuring Recommendation Explanation Quality." SIGIR 2020. [doi](https://doi.org/10.1145/3397271.3401032) *(meta)*.
- **Faithfulness risks.**
  - Turpin et al. "Language Models Don't Always Say What They Think." NeurIPS 2023. [arXiv 2305.04388](https://arxiv.org/abs/2305.04388).
  - Kabongo and Guigue on the low factual precision of generated recommendation explanations. [arXiv 2512.24366](https://arxiv.org/abs/2512.24366).
- **Why-not explanations.** Ghazimatin et al., PRINCE, WSDM 2020. [doi](https://doi.org/10.1145/3336191.3371824) *(meta)*. FoodSwap's why-not drawer is a simple, data-grounded form.

## 8. Allergen information reliability

- **DunnGalvin et al.** "Precautionary allergen labelling: perspectives from key stakeholder groups." *Allergy* 70(9) (2015). [doi](https://doi.org/10.1111/all.12614). "May contain" labelling is applied inconsistently without agreed reference doses and correlates poorly with actual risk.
- **Ford et al.** "Food allergen advisory labeling and product contamination with egg, milk, and peanut." *JACI* 126 (2010). [doi](https://doi.org/10.1016/j.jaci.2010.05.034) *(meta)*. Allergen was detected in some products with and without advisory labels *(exact rates unverified)*. The absence of a "may contain" statement is not evidence of absence.
- **Codex Alimentarius** adopted guidelines on precautionary allergen labelling in July 2026 ([CCFL](https://codex.fao.org/codex-committees/general-subject-committees/CCFL)). Practice is still being harmonized, so the "traces" field is heterogeneous.
- **Open Food Facts' preference matching** distinguishes `unknown_match`, `may_not_match` and `does_not_match` ([docs](https://openfoodfacts.github.io/openfoodfacts-server/dev/explain-personal-search)). This is a direct precedent for our policy.
- **LLM dietary advice.** Niszczota and Rybicka, "The credibility of dietary advice formulated by ChatGPT: Robo-diets for people with food allergies," *Nutrition* (2023). [doi](https://doi.org/10.1016/j.nut.2023.112076) *(meta)*. Generated allergy-safe menus included allergens.
- **Gap.** No peer-reviewed audit of the accuracy of Open Food Facts allergen fields was found. The hand audit (S2) is therefore a small contribution.

## 9. Evaluation methodology

| Topic | Reference | What we take |
|---|---|---|
| Graded relevance and nDCG | Järvelin and Kekäläinen, *TOIS* 2002. [doi](https://doi.org/10.1145/582415.582418) | Primary metric (cited in the proposal) |
| Incomplete judgments | Sakai, "Alternatives to Bpref," SIGIR 2007. [doi](https://doi.org/10.1145/1277741.1277756) *(meta)* | Condensed lists as a robustness check; Judged@k |
| Assessor disagreement | Voorhees, *IP&M* 2000. [doi](https://doi.org/10.1016/S0306-4573%2800%2900010-8) *(meta)* | System rankings stay stable despite disagreement |
| Number of topics | Voorhees and Buckley, SIGIR 2002. [doi](https://doi.org/10.1145/564376.564432) *(meta)*; Sakai, "Topic set size design," *Information Retrieval Journal* (2016). [doi](https://doi.org/10.1007/s10791-015-9273-z) *(meta)* | About 50 topics is the classic floor; we state the MDE for 20 |
| Significance tests | Smucker, Allan, Carterette, CIKM 2007. [doi](https://doi.org/10.1145/1321440.1321528) *(meta)*; Urbano, Lima, Hanjalić, SIGIR 2019. [doi](https://doi.org/10.1145/3331184.3331259) *(meta)* | Paired randomization or t-test; avoid sign and Wilcoxon tests |
| Multiple comparisons | Carterette, *TOIS* 2012. [doi](https://doi.org/10.1145/2094072.2094076) *(meta)* | Holm correction across ablations |
| Common mistakes | Fuhr, "Some Common Mistakes in IR Evaluation," *SIGIR Forum* (2017). [doi](https://doi.org/10.1145/3190580.3190586) *(meta)* | Report effect sizes; never tune on test topics |
| Rank similarity | Webber, Moffat, Zobel, "A similarity measure for indefinite rankings," *TOIS* 2010. [doi](https://doi.org/10.1145/1852102.1852106) *(meta)* | RBO for paraphrase robustness |
| Beyond-accuracy metrics | Kaminskas and Bridge, *TiiS* 2016. [doi](https://doi.org/10.1145/2926720) *(meta)* | Diversity and coverage definitions |
| LLMs as judges | Thomas, Spielman, Craswell, Mitra, SIGIR 2024. [doi](https://doi.org/10.1145/3626772.3657707) *(meta)*; UMBRELA, [arXiv 2406.06519](https://arxiv.org/abs/2406.06519); TREC 2024 RAG judging study, [arXiv 2411.08275](https://arxiv.org/abs/2411.08275); Faggioli et al., ICTIR 2023, [doi](https://doi.org/10.1145/3578337.3605136) | LLM labels can reproduce system rankings well |
| Cautions on LLM judges | Soboroff, [arXiv 2409.15133](https://arxiv.org/abs/2409.15133); Clarke and Dietz, [arXiv 2412.17156](https://arxiv.org/abs/2412.17156); Alaofi et al., [arXiv 2501.17969](https://arxiv.org/abs/2501.17969); Dietz et al., "LLM-Evaluation Tropes," [arXiv 2504.19076](https://arxiv.org/abs/2504.19076) | Circularity, keyword-stuffing gullibility, continuous human validation: the protocol in [09](09-evaluation.md#10-optional-llm-as-a-second-judge-stretch) |
| User-study instruments | Pu, Chen, Hu, "ResQue," RecSys 2011. [doi](https://doi.org/10.1145/2043932.2043962) *(meta)*; SUS; UEQ-S | For a future user study (Later) |

## 10. Existing products

| Product | How it chooses alternatives | Constraints the user can set | Transparency |
|---|---|---|---|
| Open Food Facts website and app | No swap feature; personal ranking by preference match ([docs](https://openfoodfacts.github.io/openfoodfacts-server/dev/explain-personal-search)) | Allergens, diets, nutrients, processing (set in advance) | High: open algorithms |
| [Yuka](https://help.yuka.io/l/en/article/s71arvkw6u-selection-recommendations) | Same category, available, rated "good" or better. Its score is 60% Nutri-Score, 30% additives, 10% organic ([scoring](https://help.yuka.io/l/en/article/ijzgfvi1jq-how-are-food-products-scored)). | None | Score breakdown; additive ratings contested |
| FoodSwitch (George Institute; SaltSwitch, GlutenSwitch) | Healthier products in the same category ranked by Health Star Rating *(unverified)* | Salt, gluten filters | Published trials |
| [NHS Food Scanner](https://www.nhs.uk/healthier-families/food-facts/nhs-food-scanner-app/) (UK) | "Good Choice" swaps; criteria not published | Sugar, saturated fat, salt | Low |
| Fig, Spokin, Spoonful, Fooducate | Allergen and diet flags; some list alternatives *(unverified)* | Allergens and diets | Varies |
| Instacart; Amazon's shopping assistant (Rufus, renamed Alexa for Shopping in May 2026 per [Amazon](https://www.aboutamazon.com/news/retail/amazon-rufus-ai-assistant-personalized-shopping-features)); Walmart Sparky; ChatGPT shopping | Acceptance models or LLM suggestions | Free text, with no guarantee about allergens | Generated text |
| Student projects on GitHub (more than 200 "Pur Beurre" style repositories) | Same category, better Nutri-Score, from the OFF API | None | — |

**What none of them do**, and FoodSwap does:

1. Parse a free-text request into hard and soft constraints.
2. Guarantee hard constraints, and abstain when evidence is missing.
3. Combine lexical and dense retrieval with similarity to a reference product, rather than "same category, better score".
4. Ground every explanation, including why-not explanations, in the record.
5. Publish an evaluation with constraint-violation metrics.

**Name check.** No app called "FoodSwap" was found. The nearest name is FoodSwitch, so the report should say the two are unrelated.

## 11. Definitions of "healthier" (background)

FoodSwap ranks on the nutrients the user names and never asserts healthiness ([07](07-constraints-and-safety.md#8-wording-rules-and-disclaimers)). The systems below are background for the report and for the X2 baseline.

| System | What it is | Usable for US products from OFF? |
|---|---|---|
| Nutri-Score, 2023 algorithm ([update report](https://mpc.gouvernement.lu/dam-assets/le-minist%C3%A8re/consodur/2022-main-algorithm-report-update-final.pdf); [beverages](https://www.santepubliquefrance.fr/sites/default/files/rdd/document/Update%20report%20beverages_31%2001%202023-VOTED.pdf)) | Points for energy, sugars, saturated fat and salt, minus protein, fibre, and fruit/vegetable/legume share, per 100 g. Classes A ≤ 0, B 1–2, C 3–10, D 11–18, E ≥ 19 for general foods; separate rules for fats and beverages. Voluntary in several EU countries; not used in the US. | Yes, as computed by OFF (the fruit/vegetable share is estimated from ingredients) |
| NOVA (Monteiro et al., *Public Health Nutrition* 2019, [doi](https://doi.org/10.1017/S1368980018003762) *(meta)*) | Four processing groups | Yes, computed by OFF; assignment consistency is debated |
| UK FSA/Ofcom nutrient profiling model | Ancestor of Nutri-Score; used for UK advertising rules | Approximately |
| Health Star Rating (Australia and New Zealand) | 0.5 to 5 stars | Approximately |
| Food Compass 2.0 (Barrett et al., *Nature Food* 2024, [doi](https://doi.org/10.1038/s43016-024-01053-3)) | 1–100 score per 100 kcal, validated against NHANES outcomes | No: needs many inputs OFF lacks |
| NRF9.3 (Fulgoni, Keast, Drewnowski, *J Nutr* 2009, [doi](https://doi.org/10.3945/jn.108.101360) *(meta)*) | Nutrients to encourage minus nutrients to limit, as % Daily Value | Partly: several vitamins are not on US labels |
| FDA "healthy" claim ([FDA](https://www.fda.gov/food/hfp-constituent-updates/fda-finalizes-updated-healthy-nutrient-content-claim)) | Food-group content plus limits on added sugars, sodium and saturated fat | No: food-group content is unavailable |
