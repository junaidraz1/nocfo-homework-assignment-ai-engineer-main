from datetime import datetime

Attachment = dict[str, dict]
Transaction = dict[str, dict]

# Helper Functions

# Normalizing reference numbers based on the requirement mentioned i.e. removing whitespaces, leading zeros
def normalizing_refnum(ref: str | None) -> str:
    if not ref:
        return ""
    
    normalized = ref.replace(" ", "").lstrip("0").upper()
    return normalized

# Noramlizing name by removing extra whitespaces (if any) and converting name into lowercase to make comparison easier
def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(name.lower().split())

# Checks similarity between the names
def names_match(name1: str | None, name2: str | None) -> bool:
    if not name1 or not name2:
        return False
    
    # Starts with normalizing the names first
    norm_name1 = normalize_name(name1)
    norm_name2 = normalize_name(name2)
    
    # Case 1: Checking for exact match
    if norm_name1 == norm_name2:
        return True
    
    # Case 2: Checking if one contains the other e.g. substring in a string for partial matches like "John" in "John Doe"
    if norm_name1 in norm_name2 or norm_name2 in norm_name1:
        return True
    
    # SCase 3: By spliting names into parts e.g. first name, last name, etc.
    parts1 = norm_name1.split()
    parts2 = norm_name2.split()
    
    # If they have different number of name parts, check if all parts of shorter name match
    if len(parts1) != len(parts2):
        shorter = parts1 if len(parts1) < len(parts2) else parts2
        longer = parts2 if len(parts1) < len(parts2) else parts1
        
        # All parts of shorter name must appear in longer name with close match
        for part in shorter:
            found_match = False
            for longer_part in longer:
                # Check for substring match or close edit distance
                if part in longer_part or longer_part in part:
                    found_match = True
                    break
                # Allow small edit distance i.e. typos based on word length
                max_dist = 1 if len(part) <= 5 else 2
                if edit_distance(part, longer_part) <= max_dist:
                    found_match = True
                    break
            if not found_match:
                return False
        return True
    
    # Same number of parts - each corresponding part must match closely
    for p1, p2 in zip(parts1, parts2):
        dist = edit_distance(p1, p2)
        # Allow max 1-2 character difference per word part depending on length
        max_allowed = 1 if len(p1) <= 5 else 2
        if dist > max_allowed:
            return False
    
    return True

# Method to calculate how different two words are based on distance,
# I used Levenshtein distance algo
# Reference: https://www.geeksforgeeks.org/python/introduction-to-python-levenshtein-module/
def edit_distance(s1: str, s2: str) -> int:
    len1, len2 = len(s1), len(s2)
    
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1
    
    # Create matrix for edit distance
    matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        matrix[i][0] = i
    for j in range(len2 + 1):
        matrix[0][j] = j
    
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if s1[i-1] == s2[j-1]:
                matrix[i][j] = matrix[i-1][j-1]
            else:
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,    
                    matrix[i][j-1] + 1,    
                    matrix[i-1][j-1] + 1  
                )
    
    return matrix[len1][len2]

# Check if two dates are within max_days of each other
def dates_close(date1_str: str | None, date2_str: str | None, max_days: int = 10) -> bool:
    if not date1_str or not date2_str:
        return False
    
    try:
        date1 = datetime.strptime(date1_str, "%Y-%m-%d")
        date2 = datetime.strptime(date2_str, "%Y-%m-%d")
        return abs((date1 - date2).days) <= max_days
    except:
        return False

# Extracts reciepient, supplier and issuer names from json
def get_counterparty_info(attachment: Attachment) -> list[str]:
    data = attachment.get("data", {})
    names = []
    
    # For invoices issued by us (sales invoices)
    if "recipient" in data and data["recipient"]:
        names.append(data["recipient"])
    
    # For invoices received (purchase invoices)
    if "issuer" in data and data["issuer"]:
        names.append(data["issuer"])
    
    # For purchase invoices with supplier field
    if "supplier" in data and data["supplier"]:
        names.append(data["supplier"])
    
    return names

# Extracts all the dates i.e. invoicing_date, due_date (for invoices) & receiving_date (for reciept)
def get_attachment_dates(attachment: Attachment) -> list[str]:
    data = attachment.get("data", {})
    dates = []
    
    if "due_date" in data and data["due_date"]:
        dates.append(data["due_date"])
    if "invoicing_date" in data and data["invoicing_date"]:
        dates.append(data["invoicing_date"])
    if "receiving_date" in data and data["receiving_date"]:
        dates.append(data["receiving_date"])
    
    return dates

# Finds invoice for a transaction
# Scoring system:
    # Amount match = +10, 
    # Date match = +7 (same day), +6 (1-2 days difference), +3 (10 days difference)
    # Best match is when score >= 17
def find_attachment(
    transaction: Transaction,
    attachments: list[Attachment],
) -> Attachment | None:
    
    # Step 1: Getting transaction info first 
    tx_ref = normalizing_refnum(transaction.get("reference"))
    tx_amount = abs(transaction.get("amount", 0)) 
    tx_date = transaction.get("date")
    tx_contact = transaction.get("contact")
    
    best_match = None
    best_score = 0
    
    # Step 2: Looping through all the invoices to give score to each of it
    for attachment in attachments:
        data = attachment.get("data", {})
        score = 0
        signals_matched = 0  # This variable is to keep track of cues such as Amount, date and counterparty info to call it a match
        
        # 1. First checking for reference number match
        att_ref = normalizing_refnum(data.get("reference"))
        if tx_ref and att_ref and tx_ref == att_ref:
            return attachment 
        
        # 2. Second checking for amount match
        att_amount = data.get("total_amount", 0)
        if abs(att_amount) != tx_amount:
            continue  # Skip if amount doesn't match
        
        score += 10  # Base score for amount match
        signals_matched += 1
        
        # 3. Third is to check how close the date is to due date
        att_dates = get_attachment_dates(attachment)
        date_matched = False
        best_date_diff = float('inf')
        for att_date in att_dates:
            if dates_close(tx_date, att_date, max_days=10):
                try:
                    d1 = datetime.strptime(tx_date, "%Y-%m-%d")
                    d2 = datetime.strptime(att_date, "%Y-%m-%d")
                    diff = abs((d1 - d2).days)
                    if diff < best_date_diff:
                        best_date_diff = diff
                except:
                    pass
                date_matched = True
        
        if date_matched:
            signals_matched += 1
            score += max(3, 7 - (best_date_diff // 2))
        
        # 4. Fourth is to check if name matches
        att_counterparties = get_counterparty_info(attachment)
        name_matched = False
        name_score = 0
        for att_name in att_counterparties:
            if names_match(tx_contact, att_name):
                signals_matched += 1
                if normalize_name(tx_contact) == normalize_name(att_name):
                    name_score = 7
                else:
                    name_score = 4
                name_matched = True
                break
        
        if name_matched:
            score += name_score
        
        # Logic here is to have 2 cues atleast AND name match OR very close date,
        # to classify as high confidence value
        if signals_matched < 2:
            continue
        
        # Logic here is if only amount + date match and no name meaning 2 out of 3 cues,
        # then it requires very close date match i.e. same day to be confident
        if not name_matched and date_matched:
            if best_date_diff > 0:
                continue
        
        # Update best match if this score is better
        if score > best_score:
            best_score = score
            best_match = attachment
    
    # Only return if we have a confident match
    # Score threshold: need at least amount (10) + strong date (5+) + name (4+) = 19+
    # OR amount (10) + perfect date (7) + good name (4) = 21+
    if best_score >= 17:
        return best_match
    
    return None

# Finds transaction for a invoice (same logic as above just in reverse)
# Scoring system:
    # Amount match = +10, 
    # Date match = +7 (same day), +6 (1-2 days difference), +3 (10 days difference)
    # Best match is when score >= 17
def find_transaction(
    attachment: Attachment,
    transactions: list[Transaction],
) -> Transaction | None:
    
    # Step 1: Getting invoice info first 
    data = attachment.get("data", {})
    att_ref = normalizing_refnum(data.get("reference"))
    att_amount = data.get("total_amount", 0)
    att_dates = get_attachment_dates(attachment)
    att_counterparties = get_counterparty_info(attachment)
    
    best_match = None
    best_score = 0
    
    for transaction in transactions:
        score = 0
        signals_matched = 0
        
        # 1. Reference number match (highest priority)
        tx_ref = normalizing_refnum(transaction.get("reference"))
        if att_ref and tx_ref and att_ref == tx_ref:
            return transaction  # Immediate match
        
        # 2. Amount match (required)
        tx_amount = abs(transaction.get("amount", 0))
        if abs(att_amount) != tx_amount:
            continue
        
        score += 10 
        signals_matched += 1
        
        # 3. Date proximity
        tx_date = transaction.get("date")
        date_matched = False
        best_date_diff = float('inf')
        for att_date in att_dates:
            if dates_close(tx_date, att_date, max_days=10):
                try:
                    d1 = datetime.strptime(tx_date, "%Y-%m-%d")
                    d2 = datetime.strptime(att_date, "%Y-%m-%d")
                    diff = abs((d1 - d2).days)
                    if diff < best_date_diff:
                        best_date_diff = diff
                except:
                    pass
                date_matched = True
        
        if date_matched:
            signals_matched += 1
            score += max(3, 7 - (best_date_diff // 2))
        
        # 4. Counterparty name match
        tx_contact = transaction.get("contact")
        name_matched = False
        name_score = 0
        for att_name in att_counterparties:
            if names_match(tx_contact, att_name):
                signals_matched += 1
                if normalize_name(tx_contact) == normalize_name(att_name):
                    name_score = 7
                else:
                    name_score = 4
                name_matched = True
                break
        
        if name_matched:
            score += name_score
        
        # Require at least 2 out of 3 signals
        if signals_matched < 2:
            continue
        
        # If only amount + date (no name), require very close date
        if not name_matched and date_matched:
            if best_date_diff > 0:  # Require same-day match without name
                continue
        
        if score > best_score:
            best_score = score
            best_match = transaction
    
    # Only return confident matches
    if best_score >= 17:
        return best_match
    
    return None