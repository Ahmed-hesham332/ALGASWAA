import pymysql.cursors
from datetime import datetime, timedelta

# ----------------------------------------------------
# 1. DATABASE CONFIGURATION (MUST BE CORRECT)
# ----------------------------------------------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'radius_user',      # Your MySQL username
    'password': 'your_strong_mysql_password', # Your MySQL password
    'database': 'radius',       # Your MySQL database name
    'cursorclass': pymysql.cursors.DictCursor,
}

def run_activation_cycle():
    print(f"--- Running Activation Cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    try:
        cnx = pymysql.connect(**DB_CONFIG)
        cursor = cnx.cursor()
    except pymysql.err.OperationalError as e:
        print(f"ERROR: Could not connect to MySQL database. Details: {e}")
        return

    try:
        # 2. SELECT QUERY: Get online, unused sessions and their duration
        SELECT_QUERY = """
        SELECT 
            a.UserName, 
            a.AcctStartTime, 
            v.duration_seconds
        FROM radacct a
        JOIN vouchers v ON a.UserName = v.voucher_number
        WHERE a.AcctStopTime IS NULL  
          AND v.status = 0;           
        """
        cursor.execute(SELECT_QUERY)
        sessions_to_activate = cursor.fetchall()
        
        if not sessions_to_activate:
            print("No new sessions to activate.")
            return

        print(f"Found {len(sessions_to_activate)} session(s) to activate.")

        for session in sessions_to_activate:
            username = session['UserName']
            start_time = session['AcctStartTime']
            duration = session['duration_seconds']

            # Calculate Final Expiration Time (T_expires = T_start + Duration)
            expiration_dt = start_time + timedelta(seconds=duration)
            expiration_str = expiration_dt.strftime("%d %b %Y %H:%M")

            try:
                # 3. A. Update Voucher Status (Mark as used and set activated_at)
                UPDATE_VOUCHER_QUERY = """
                UPDATE vouchers
                SET status = 1, activated_at = NOW()
                WHERE voucher_number = %s AND status = 0;
                """
                cursor.execute(UPDATE_VOUCHER_QUERY, (username,))

                # 3. B. Insert Expiration Attribute (radcheck)
                INSERT_RADCHECK_QUERY = """
                INSERT INTO radcheck (username, attribute, op, value)
                VALUES (%s, 'Expiration', ':=', %s);
                """
                cursor.execute(INSERT_RADCHECK_QUERY, (username, expiration_str))

                # 3. C. Delete Temporary Session-Timeout (radreply)
                DELETE_RADREPLY_QUERY = """
                DELETE FROM radreply 
                WHERE UserName = %s AND Attribute = 'Session-Timeout';
                """
                cursor.execute(DELETE_RADREPLY_QUERY, (username,))
                
                cnx.commit()
                print(f"    SUCCESS: {username} activated. Expires at {expiration_str}. Timeout removed.")

            except Exception as e:
                print(f"    ROLLBACK ERROR processing {username}: {e}")
                cnx.rollback() # Safely undo changes for this user

    except Exception as e:
        print(f"CRITICAL ERROR during query execution: {e}")
        
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'cnx' in locals() and cnx:
            cnx.close()

if __name__ == "__main__":
    run_activation_cycle()
