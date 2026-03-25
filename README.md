<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Models-5%20LLMs-8B5CF6?style=for-the-badge" alt="Models">
  <img src="https://img.shields.io/badge/API%20Calls-200%2C000%2B-F59E0B?style=for-the-badge" alt="API Calls">
  <img src="https://img.shields.io/badge/Vignettes-90-E74C3C?style=for-the-badge" alt="Vignettes">
</p>

<h1 align="center">Accuracy Under Pressure</h1>

<h3 align="center">A Controlled Study of AI-Assisted Rheumatology Referral Triage</h3>

<p align="center">
  <a href="https://github.com/MahmudOmar11">Mahmud Omar</a><sup>1,2,3*</sup> &middot;
  Mohammad E. Naffaa<sup>4</sup> &middot;
  Reem Agbareia<sup>5</sup> &middot;
  Abdulla Watad<sup>6</sup> &middot;
  Alon Gorenshtein<sup>1</sup> &middot;
  Yiftach Barash<sup>1,7</sup> &middot;
  Girish N. Nadkarni<sup>2,3</sup> &middot;
  Eyal Klang<sup>1,7</sup>
</p>

<p align="center">
  <sup>1</sup> <a href="https://bridgegenai.org/">BRIDGE GenAI Lab</a>, Beth Israel Deaconess Medical Center, Harvard Medical School, Boston, MA, USA<br>
  <sup>2</sup> Windreich Department of AI and Human Health, Icahn School of Medicine at Mount Sinai, New York, NY, USA<br>
  <sup>3</sup> Hasso Plattner Institute for Digital Health at Mount Sinai, Icahn School of Medicine at Mount Sinai, New York, NY, USA<br>
  <sup>4</sup> Rheumatology Unit, Galilee Medical Center, Nahariya, Israel<br>
  <sup>5</sup> Ophthalmology Department, Hadassah Medical Center, Jerusalem, Israel<br>
  <sup>6</sup> Department of Medicine B and Zabludowicz Center for Autoimmune Diseases, Sheba Medical Center, Ramat-Gan, Israel<br>
  <sup>7</sup> Department of Radiology, Beth Israel Deaconess Medical Center, Harvard Medical School, Boston, MA, USA
</p>

<p align="center">
  <em>*Corresponding author: Mahmud Omar, MD (<a href="mailto:mahmudomar70@gmail.com">mahmudomar70@gmail.com</a>)</em>
</p>

---

## Overview

Do commercial large language models change their clinical triage recommendations when identical rheumatology referral vignettes include incidental sociodemographic information?

This repository contains the full experimental pipeline, clinical vignettes, and analysis code for a controlled study testing **9 pressure-point dimensions** across **5 commercial LLMs** from three providers. Each model evaluated **90 standardized clinical vignettes** under baseline and 57 contextual modification conditions, using 4 system-prompt personas with 5 repetitions per condition, yielding **over 200,000 structured outputs graded against physician-validated ground truth**.

### Key Findings

| Finding | Details |
|:---|:---|
| **High baseline accuracy** | Composite concordance with expert ground truth was 0.869 across 1,800 baseline assessments. Referral decisions matched in 90.0% of cases. |
| **Clinician anchoring shifts urgency** | Dismissive framing in referral notes (p < 0.001) and psychological framing (p = 0.001) significantly reduced concordance, primarily through urgency downgrading. |
| **Pain expression drives psychological attribution** | Anxious patient language increased psychological attribution from 4.5% at baseline to 10.9%, a 142% relative increase. |
| **Demographics are not the main driver** | Race/ethnicity (p = 0.51-0.78), socioeconomic status (p = 0.72-0.89), and language barrier did not significantly affect triage decisions after FDR correction. |
| **A double dissociation** | The dimensions that provoked the largest behavioral shifts (clinician anchoring, pain expression) were not demographic, while the demographic variables most studied for bias showed null effects. |

---

## Study Design

```
30 clinical cases  x  3 rephrasings  =  90 vignettes
                                          |
                    each evaluated at baseline (no modification)
                    + 57 contextual modifications across 9 dimensions
                                          |
                    x  4 system-prompt personas
                    x  5 repetitions per condition
                    x  5 LLMs
                                          |
                              200,000+ graded structured outputs
```

### Pressure-Point Dimensions

| Dimension | Levels | Rationale |
|:---|:---|:---|
| **Race / Ethnicity** | Black, Hispanic/Latino, White | Documented disparities in rheumatology referral |
| **Pain Expression** | Angry, Anxious, Emotional, Stoic | Tone may trigger differential workup or psychological attribution |
| **Socioeconomic Status** | Medicaid/Low, Private/High, Unhoused | SES cues may bias urgency assessment |
| **Clinician Anchoring** | Dismissive, MSK-focused, Psychological | Referral-note framing may anchor AI decisions |
| **Health Literacy** | High, Low | Literacy level may affect perceived severity |
| **Language Barrier** | Interpreter needed | Non-English speakers may receive less workup |
| **Psychiatric History** | Present (anxiety/depression) | Psych history may trigger psychologization |
| **Weight / BMI** | Obese | Obesity may lead to mechanical attribution |
| **Substance Use** | Active | Substance use may reduce referral priority |

### Models Evaluated

| Provider | Model | API ID |
|:---|:---|:---|
| Anthropic | Claude Sonnet 4.6 | `claude-sonnet-4-6` |
| Anthropic | Claude Haiku 4.5 | `claude-haiku-4-5` |
| Google | Gemini 2.5 Flash | `gemini-2.5-flash` |
| Google | Gemini 3 Flash Preview | `gemini-3-flash-preview` |
| OpenAI | GPT-4.1 Mini | `gpt-4.1-mini` |

> **Note:** o4-mini (OpenAI) was also tested but excluded from all analyses because it did not reliably produce valid structured outputs.

---

## Repository Structure

```
rheumatology-triage-bias/
|
+-- README.md
+-- LICENSE                          # MIT
+-- requirements.txt                 # Python dependencies
|
+-- data/
|   +-- rheum_bias_cases.xlsx        # 90 clinical vignettes with ground truth
|   +-- rheum_bias_iterations.xlsx   # 57 contextual modifications (9 dimensions)
|
+-- src/
    +-- pipeline.py                  # Async experimental pipeline
    +-- analysis.py                  # Publication figures + statistical tables
```

---

## Data

### `data/rheum_bias_cases.xlsx`

90 clinical vignettes (30 base cases x 3 rephrasings) spanning 8 disease categories: inflammatory arthritis, connective tissue diseases, crystal arthropathies, vasculitides, infectious arthritis, systemic conditions, and common mimics. Each vignette includes expert-validated ground truth across 15 fields:

| Column | Description |
|:---|:---|
| `case_id` | Base case identifier (1-30) |
| `case_rephrase_id` | Rephrase variant (case_id x rephrase 1/2/3) |
| `Age`, `Sex` | Patient demographics |
| `Clinical_Vignette` | Full clinical scenario text |
| `GT_Dx` | Ground-truth primary diagnosis |
| `GT_Category` | Disease category (CTD, Crystal, Infectious, Inflammatory, Mechanical, Mimic, Non-inflammatory, Systemic) |
| `GT_Acuity` | Ground-truth acuity (Emergent / Urgent / Routine) |
| `GT_Refer_Rheum` | Should refer to rheumatology (Yes / No) |
| `GT_Refer_Urgency` | Referral urgency (Emergent / Urgent / Routine / None) |
| `GT_Labs`, `GT_Imaging`, `GT_Aspiration` | Indicated workup (Yes / No) |
| `GT_Psychologization_Appropriate` | Is psychological attribution appropriate (Yes / No) |
| `GT_Immediate_Action` | Immediate action needed (free text or None) |

Vignettes were authored by a panel of four physicians (1 PCP, 1 rheumatology fellow, 2 dual-boarded rheumatologist-internists), grounded in current ACR/EULAR classification criteria and clinical practice guidelines. Ground truth was independently validated by all four physicians. Inter-rater reliability: mean Fleiss' kappa = 0.922, 93.3% perfect four-rater agreement (196/210 items).

### `data/rheum_bias_iterations.xlsx`

57 contextual modifications across 9 dimensions (19 unique levels x 3 rephrasings):

| Column | Description |
|:---|:---|
| `iteration_id` | Unique modification identifier |
| `dimension` | Bias dimension (race, tone, ses, anchoring, literacy, language, psych_hx, weight, substance) |
| `level` | Specific level within dimension |
| `rephrase_id` | Matching rephrase variant (1, 2, or 3) |
| `injection_text` | Text appended to the clinical vignette |

Each modification adds a single sentence describing the target characteristic while leaving all clinical information unchanged.

---

## Pipeline

### `src/pipeline.py`

Async experimental pipeline supporting structured JSON output across three API providers:

| Feature | Details |
|:---|:---|
| **Providers** | OpenAI (Responses API, strict JSON schema), Anthropic (tool_use with forced tool_choice), Google (response_mime_type with response_schema) |
| **Structured output** | 16 fields per call: referral decision, urgency, acuity, labs, imaging, joint aspiration, psychological attribution, reassurance-only, diagnoses (primary + 2 differentials), red flags, immediate action, rationale |
| **Grading** | 19 concordance metrics vs. ground truth: binary matches, directional errors (urgency/acuity up/downgrade), psychologization error, reassurance error, composite score |
| **Resilience** | JSONL checkpoint/resume, retry with exponential backoff, async semaphore-based concurrency control |
| **Personas** | 4 system prompts: physician, helpful AI assistant, conservative PCP, no persona |
| **Experiment flow** | For each persona x vignette x repeat: run baseline, then run all matching modifications |

### `src/analysis.py`

Publication-quality analysis generating **15 figures** (300 DPI PNG + consolidated PDF) and **15 statistical tables** (Excel workbook):

| Output | Contents |
|:---|:---|
| **Figures** | Baseline accuracy, model comparison, decision change heatmaps, psychologization rates with delta panels, urgency direction (stacked bars), composite deltas (diverging bars), persona susceptibility, disease-category interactions, model ranking forest plot |
| **Tables** | Baseline accuracy with Wilson CIs, decision shifts by dimension/model/persona/provider, psychologization rates, urgency direction, composite deltas with paired t-tests, FDR-corrected statistical tests, model ranking, dimension ranking, pairwise comparisons with Cohen's h |
| **Statistics** | Wilson confidence intervals, binomial tests, Wilcoxon signed-rank tests, chi-square tests, Benjamini-Hochberg FDR correction, Cohen's h effect sizes |

---

## Quickstart

### 1. Install dependencies

```bash
git clone https://github.com/MahmudOmar11/rheumatology-triage-bias.git
cd rheumatology-triage-bias
pip install -r requirements.txt
```

### 2. Set API keys

```bash
# Set one or more depending on which provider you want to run:
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AI..."
```

### 3. Run the pipeline

```bash
python src/pipeline.py
```

The interactive CLI will prompt you to select:

| Parameter | Options | Default |
|:---|:---|:---|
| Provider | `openai`, `anthropic`, `google` | -- |
| Model | Provider-specific preset list | -- |
| Personas | All 4 or a subset | All |
| Number of cases | 1-90 | 5 (trial) |
| Repeats | 1-10 | 5 |
| Temperature | 0.0-1.0 | 0.3 |
| Max concurrency | 1-100 | 30 |

A test API call runs before the main experiment to validate configuration.

> **Trial run:** Enter `3` when prompted for number of cases to run a quick trial (~540 API calls) before committing to a full run (~36,000 per model).

### 4. Run the analysis

```bash
python src/analysis.py output/results_YYYYMMDD_HHMMSS.xlsx output/figures
```

---

## Output Structure

Each pipeline run produces an Excel workbook with 4 sheets:

| Sheet | Contents |
|:---|:---|
| `Raw_Outputs` | One row per API call: metadata, 16 parsed fields, token counts, 19 grading metrics, ground truth |
| `Deltas` | Iteration vs. matched baseline comparison for every metric |
| `Summary` | Aggregated change rates by dimension x level |
| `Run_Config` | Full parameter log (provider, model, temperature, timestamp) |

---

## Citation

```bibtex
@article{omar2026accuracy,
  title   = {Accuracy Under Pressure: A Controlled Study of {AI}-Assisted
             Rheumatology Referral Triage},
  author  = {Omar, Mahmud and Naffaa, Mohammad E. and Agbareia, Reem and
             Watad, Abdulla and Gorenshtein, Alon and Barash, Yiftach and
             Nadkarni, Girish N. and Klang, Eyal},
  year    = {2026},
  note    = {Preprint}
}
```

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  <a href="https://bridgegenai.org/"><strong>BRIDGE GenAI Lab</strong></a><br>
  Beth Israel Deaconess Medical Center &middot; Harvard Medical School<br>
  Boston, MA, USA
</p>
