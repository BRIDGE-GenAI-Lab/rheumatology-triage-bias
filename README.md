<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Models-5%20LLMs-8B5CF6?style=for-the-badge" alt="Models">
  <img src="https://img.shields.io/badge/API%20Calls-200%2C000%2B-F59E0B?style=for-the-badge" alt="API Calls">
</p>

<h1 align="center">Sociodemographic Bias in LLM-Based<br>Rheumatology Triage</h1>

<p align="center">
  <strong>A controlled factorial experiment measuring how contextual modifications<br>to clinical vignettes shift AI triage decisions in rheumatology referrals</strong>
</p>

<p align="center">
  <a href="https://github.com/MahmudOmar11">Mahmud Omar, MD</a> &middot;
  Raed Omar &middot;
  Eyal Kimhi, MD
</p>

<p align="center">
  <a href="https://bridge.seas.harvard.edu">BRIDGE GenAI Lab</a><br>
  Beth Israel Deaconess Medical Center &middot; Harvard Medical School<br>
  Boston, MA, USA
</p>

---

## Overview

Do commercial large language models change their clinical triage recommendations when identical rheumatology referral vignettes include incidental sociodemographic information?

This repository contains the full experimental pipeline, clinical vignettes, and analysis code for a controlled study testing **9 sociodemographic pressure-point dimensions** across **5 commercial LLMs** from three providers. Each model evaluated **90 standardized clinical vignettes** under baseline and 57 contextual modification conditions, using 4 system-prompt personas with 5 repetitions per condition, yielding **over 200,000 graded API calls**.

### Key Findings

- **Demographics do not drive bias.** Race/ethnicity, socioeconomic status, and weight/BMI produced no statistically significant shifts in triage decisions after FDR correction.
- **Clinician framing does.** Dismissive or psychologically anchored referral language from the referring clinician significantly altered urgency assessments and referral recommendations.
- **Pain expression matters.** Emotional, angry, or anxious patient tone increased inappropriate psychological attribution from 1.2% at baseline to 5.6%.
- **A double dissociation.** The dimensions that provoked the largest behavioral shifts (clinician anchoring, pain expression) were not demographic, while the demographic variables most studied for bias (race, SES) showed null effects.

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
                              ~200,000+ total API calls
```

### Pressure-Point Dimensions

| Dimension | Levels | Rationale |
|:---|:---|:---|
| **Race / Ethnicity** | Black, Hispanic, White | Documented disparities in rheumatology referral |
| **Pain Expression (Tone)** | Angry, Anxious, Emotional, Stoic | Tone may trigger differential workup or psychological attribution |
| **Socioeconomic Status** | High SES, Low SES, Unhoused | SES cues may bias urgency assessment |
| **Clinician Anchoring** | Dismissive, MSK, Psychiatric | Prior clinician framing may anchor AI decisions |
| **Health Literacy** | High, Low | Literacy level may affect perceived severity |
| **Language Barrier** | Present | Non-English speakers may receive less workup |
| **Psychiatric History** | Present | Psych history may trigger psychologization |
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

### `data/rheum_bias_cases.xlsx`

90 clinical vignettes (30 base cases x 3 rephrasings) with expert-validated ground truth across 15 fields:

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

Ground truth was validated by a panel of 4 independent reviewers (1 PCP, 1 rheumatology fellow, 2 dual-trained rheumatologists). Inter-rater reliability: mean Fleiss' kappa = 0.922, Krippendorff's alpha = 0.937 (all fields "Almost Perfect").

### `data/rheum_bias_iterations.xlsx`

57 contextual modification texts mapped across 9 sociodemographic dimensions:

| Column | Description |
|:---|:---|
| `iteration_id` | Unique modification identifier |
| `dimension` | Bias dimension (race, tone, ses, anchoring, literacy, language, psych_hx, weight, substance) |
| `level` | Specific level within dimension |
| `rephrase_id` | Matching rephrase variant (1, 2, or 3) |
| `injection_text` | Text appended to the clinical vignette |

### `src/pipeline.py`

Async experimental pipeline supporting structured JSON output across three API providers:

| Feature | Details |
|:---|:---|
| **Providers** | OpenAI (Responses API), Anthropic (tool_use), Google (response_schema) |
| **Output** | 16 structured JSON fields per call (referral, urgency, labs, imaging, aspiration, psychological attribution, acuity, diagnoses, rationale) |
| **Grading** | 19 concordance metrics computed against ground truth (binary matches, directional errors, composite score) |
| **Resilience** | JSONL checkpoint/resume, retry with exponential backoff, async concurrency control |
| **Personas** | 4 system prompts (physician, helpful AI, conservative PCP, no persona) |

### `src/analysis.py`

Publication-quality analysis generating **15 figures** (300 DPI PNG + consolidated PDF) and **15 statistical tables** (Excel workbook):

**Figures:** baseline accuracy, model comparison, decision change heatmaps, psychologization rates, urgency direction, composite deltas, persona susceptibility, disease-dimension interactions, model ranking forest plot, and more.

**Tables:** baseline accuracy with Wilson CIs, decision shifts by dimension/model/persona/provider, psychologization rates, urgency direction, composite deltas with paired tests, statistical tests with FDR correction, model ranking, dimension ranking, pairwise comparisons with Cohen's h.

**Statistical methods:** Wilson confidence intervals, binomial tests, Wilcoxon signed-rank tests, chi-square tests, Benjamini-Hochberg FDR correction, Cohen's h effect sizes.

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

A test API call runs before the main experiment to catch configuration errors early.

> **Trial run (recommended first):** When prompted for number of cases, enter `3` for a quick trial (~540 API calls instead of ~36,000 per model).

### 4. Run the analysis

```bash
python src/analysis.py output/results_YYYYMMDD_HHMMSS.xlsx output/figures
```

This generates 15 publication-quality figures, 15 statistical tables, and a consolidated PDF.

---

## Pipeline Details

### Experiment Flow

```
For each persona (4):
  For each case vignette (up to 90):
    For each repeat (5):
      1. BASELINE: vignette without modification -> grade vs ground truth
      2. For each matching modification (19 per rephrase):
           ITERATION: vignette + modification -> grade vs ground truth
```

### Structured Output Enforcement

Each provider uses its native structured output mechanism to ensure consistent, parseable JSON:

| Provider | Method | Schema |
|:---|:---|:---|
| OpenAI | Responses API with `text.format` JSON schema (strict mode) | 16-field flat schema |
| Anthropic | `tool_use` with forced `tool_choice` | Tool definition with 16 parameters |
| Google | `response_mime_type="application/json"` with `response_schema` | Gemini schema dict |

### Grading Metrics (19 Concordance Measures)

Each response is graded against expert ground truth:

| Category | Metrics |
|:---|:---|
| **Binary concordance** | Referral match, urgency match, labs match, imaging match, aspiration match, acuity match, diagnosis (primary + top-3) |
| **Directional errors** | Urgency downgrade/upgrade, acuity downgrade/upgrade, under-referral, over-referral |
| **Attribution errors** | Psychologization error (model attributes to psych when GT says No), reassurance error (reassurance-only when workup indicated) |
| **Composite score** | Weighted mean of binary concordance + ordinal distance penalties (0-1 scale) |

### Checkpoint and Resume

The pipeline writes each API response to a JSONL checkpoint file as it completes. If a run is interrupted, re-running with the same output directory will skip already-completed calls and resume automatically.

---

## Output Structure

Each pipeline run produces an Excel workbook with 4 sheets:

| Sheet | Description |
|:---|:---|
| `Raw_Outputs` | One row per API call: metadata, 16 parsed fields, API stats, 19 grading metrics, ground truth |
| `Deltas` | Iteration vs. matched baseline comparison for every metric |
| `Summary` | Aggregated change rates by dimension x level |
| `Run_Config` | Full parameter log (provider, model, temperature, timestamp, etc.) |

---

## Citation

If you use this code or data, please cite:

```bibtex
@article{omar2026rheum_triage_bias,
  title   = {Clinician Framing and Patient Pain Expression, Not Demographics,
             Drive {AI} Triage Decisions in Rheumatology},
  author  = {Omar, Mahmud and Omar, Raed and Kimhi, Eyal},
  year    = {2026},
  note    = {Preprint}
}
```

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  <a href="https://bridge.seas.harvard.edu"><strong>BRIDGE GenAI Lab</strong></a><br>
  Beth Israel Deaconess Medical Center &middot; Harvard Medical School
</p>
