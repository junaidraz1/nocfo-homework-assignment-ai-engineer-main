### Instructions to Run the App

#### Running the Application
```python
python run.py
```
### Solution Overview

#### 1. Multi-Signal Scoring System
Implemented a weighted scoring approach that evaluates multiple signals:
- **Reference Number**: Instant match when present (normalized: removes spaces/leading zeros)
- **Amount match**: +10 points (required baseline - candidates rejected if amount doesn't match)
- **Date proximity**: +3 to +7 points based on how close the dates are
  - Same day: +7 points
  - 1-2 days apart: +6 points
  - 3-4 days apart: +5 points
  - 5-10 days apart: +3 points
- **Name match**: +4 to +7 points
  - Exact match: +7 points
  - Fuzzy match (minor typos): +4 points

**Confidence Threshold:** A minimum score of 17 points is required to return a match. This threshold ensures that matches have strong evidence from multiple signals rather than weak matches from a single cue.

**Multi-Signal Requirement:** At least 2 out of 3 signals must match (amount is always required, plus either date or name). When only amount and date match without name confirmation, the date must be exact same day (0 days difference) to prevent false positives with duplicate amounts

#### 2. Reference Number Normalization
Reference numbers are normalized by removing whitespace, stripping leading zeros, and converting to uppercase. This handles format variations like `"9876 543 2103"` vs `"98765432103"`.

```python
def normalizing_refnum(ref: str | None) -> str:
    if not ref:
        return ""
    normalized = ref.replace(" ", "").lstrip("0").upper()
    return normalized
```

#### 3. Fuzzy Name Matching
Uses Levenshtein edit distance algorithm to handle minor typos while rejecting significantly different names:
- Short words (≤5 letters): max 1 character difference allowed
- Long words: max 2 character differences allowed
- Handles company suffixes (e.g., "Company" vs "Company Oy")

The edit distance algorithm was implemented to handle name matching more precisely. The initial fuzzy matching logic was too lenient, incorrectly matching transaction 2006 with attachment 3005 despite having different names ("Meittiläinen" vs "Meikäläinen"). 

This algorithm calculates the minimum number of character edits (insertions, deletions, substitutions) required to transform one string into another. It applies strict thresholds based on word length:
- Words ≤5 characters: maximum 1 character difference allowed
- Words >5 characters: maximum 2 character differences allowed

This approach correctly accepts minor typos like "Meikäläinen" vs "Meikaläinen" (1 edit) while rejecting substantially different names like "Meikäläinen" vs "Meittiläinen" (3 edits), preventing false positive matches in real-world scenarios.

#### 4. Multiple Date Field Support
Checks all available date fields (`invoicing_date`, `due_date`, `receiving_date`) because payment timing varies in real-world scenarios (early payment, late payment, processing delays). Uses the closest matching date for scoring.

#### 5. Absolute Value for Amounts
Uses `abs()` on transaction amounts since transactions appear as negative (outgoing) or positive (incoming), while invoices always show positive amounts.

#### Note: 
1. AI was used for documentation refinement and code clarity. The README file was paraphrased using AI for better readability, and code comments were refined for clarity.
2. The core matching logic and scoring system were developed independently, drawing from experience with a similar but different task i.e. sentiment classification scoring system in a previous LLM-based NLP research project of mine. AI was used to brainstorm potential improvements to this initial approach.
3. For the name matching challenge I face a false positive issue (like transaction 2006 matching attachment 3005). To prevent it, the Levenshtein edit distance algorithm was researched online (reference URL included in code). AI assisted in refactoring the implementation by suggesting clearer method and variable names to improve code readability.
4. The matching strategy, algorithm selection, and core implementation decisions were made independently with AI serving as a tool for refinement and clarity rather than solution generation.