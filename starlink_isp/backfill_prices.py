import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'starlink_isp.settings')
django.setup()

from vouchers.models import Voucher

def backfill_prices():
    vouchers = Voucher.objects.exclude(offer__isnull=True)
    count = 0
    updated = 0
    
    print(f"Found {vouchers.count()} vouchers with current offers.")
    
    for v in vouchers:
        if v.offer:
            v.sold_price = v.offer.price
            v.save(update_fields=['sold_price'])
            updated += 1
            
    print(f"Successfully backfilled prices for {updated} vouchers.")

if __name__ == "__main__":
    backfill_prices()
