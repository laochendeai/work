import sqlite3
import json
import logging
from scraper.fetcher import PlaywrightFetcher
from scraper.ccgp_parser import CCGPAnnouncementParser
from extractor.cleaner import DataCleaner

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_missing_phones():
    db_path = 'data/gp.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Get cards with no phone
    logger.info("Querying cards with missing phones...")
    query = """
    SELECT bc.id, bc.company, bc.contact_name, a.url, a.id as ann_id
    FROM business_cards bc
    JOIN business_card_mentions bcm ON bc.id = bcm.business_card_id
    JOIN announcements a ON bcm.announcement_id = a.id
    WHERE (bc.phones_json IS NULL OR bc.phones_json = '[]' OR bc.phones_json = '')
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Deduplicate by URL to save requests
    url_map = {} # url -> list of (card_id, contact_name, company)
    for row in rows:
        url = row['url']
        if url not in url_map:
            url_map[url] = []
        url_map[url].append({
            'card_id': row['id'],
            'name': row['contact_name'],
            'company': row['company']
        })
    
    logger.info(f"Found {len(rows)} cards to fix, across {len(url_map)} URLs.")

    fetcher = PlaywrightFetcher()
    parser = CCGPAnnouncementParser()
    cleaner = DataCleaner()
    
    fixed_count = 0
    
    try:
        fetcher.start()
        
        for i, (url, cards) in enumerate(url_map.items()):
            logger.info(f"Processing [{i+1}/{len(url_map)}] {url}")
            
            try:
                html = fetcher.get_page(url)
                if not html: 
                    continue
                    
                parsed = parser.parse(html, url)
                formatted = parser.format_for_storage(parsed)
                
                # We need to find the phones for the specific contacts in 'cards'
                # We look at agent_contacts_list, buyer info, project contacts
                
                # Flatten all extracted contacts
                extracted_contacts = []
                
                # Buyer
                buyer_name = formatted.get('buyer_name', '')
                buyer_contact = formatted.get('buyer_contact', '')
                buyer_phones = parser._extract_extended_phones(formatted.get('buyer_phone', ''))
                if buyer_name:
                    extracted_contacts.append({'company': buyer_name, 'name': buyer_contact, 'phones': buyer_phones})
                
                # Agent
                agent_name = formatted.get('agent_name', '')
                agent_list = formatted.get('agent_contacts_list', [])
                # If explicit list
                if agent_list:
                    for c in agent_list:
                        # phone is string "p1, p2"
                        p_str = c.get('phone', '')
                        p_list = parser._extract_extended_phones(p_str)
                        extracted_contacts.append({'company': agent_name, 'name': c.get('name'), 'phones': p_list})
                # Fallback main agent contact
                if formatted.get('agent_contact'):
                    p_str = formatted.get('agent_phone', '')
                    p_list = parser._extract_extended_phones(p_str)
                    extracted_contacts.append({'company': agent_name, 'name': formatted.get('agent_contact'), 'phones': p_list})
                
                # Project
                project_contacts = formatted.get('project_contacts', [])
                proj_phones_main = parser._extract_extended_phones(formatted.get('project_phone', ''))
                
                if isinstance(project_contacts, list) and project_contacts and isinstance(project_contacts[0], dict):
                    for item in project_contacts:
                         p_list = parser._extract_extended_phones(item.get('phone', ''))
                         if not p_list and proj_phones_main: p_list = proj_phones_main
                         extracted_contacts.append({'company': item.get('company', ''), 'name': item.get('name'), 'phones': p_list}) # Company might be inferred later
                
                # Now match
                for card in cards:
                    target_name = card['name']
                    target_company = card['company']
                    card_id = card['card_id']
                    
                    best_match_phones = []
                    
                    for candidate in extracted_contacts:
                        c_name = candidate.get('name', '')
                        c_company = candidate.get('company', '')
                        c_phones = candidate.get('phones', [])
                        
                        if not c_phones: continue
                        
                        name_match = target_name in c_name or c_name in target_name
                        company_match = target_company in c_company or c_company in target_company
                        
                        if name_match and company_match:
                            best_match_phones = c_phones
                            break
                    
                    if best_match_phones:
                        # Update DB
                        # Need to merge with existing logic? Existing is empty, so just set.
                        phones_json = json.dumps(best_match_phones)
                        cursor.execute("UPDATE business_cards SET phones_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (phones_json, card_id))
                        logger.info(f"Fixed Card {card_id} ({target_name}): Found phones {best_match_phones}")
                        fixed_count += 1
                        
                conn.commit()

            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                
    finally:
        fetcher.stop()
        conn.close()
        
    logger.info(f"Done. Fixed {fixed_count} cards.")

if __name__ == '__main__':
    fix_missing_phones()
