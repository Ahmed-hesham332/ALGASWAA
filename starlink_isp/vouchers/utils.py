from django.utils import timezone
from datetime import timezone as dt_timezone
from vouchers.models import Voucher
from radius_integration.services import add_radius_expiration
from dateutil.relativedelta import relativedelta
from django.db import connections
import random
import string


def generate_serial(length=8, serial_type="numeric", prefix=""):
    max_attempts = 20  # avoid infinite loops

    for _ in range(max_attempts):

        # Generate body
        if serial_type == "numeric":
            body = ''.join(random.choices(string.digits, k=length))
        else:
            chars = string.ascii_uppercase + string.digits
            body = ''.join(random.choices(chars, k=length))

        serial = f"{prefix}{body}"

        # Check DB
        if not Voucher.objects.filter(serial=serial).exists():
            return serial

    # If many failures → raise error (extremely rare)
    raise ValueError("Unable to generate unique serial. Increase length or change type.")


def update_voucher_status():
    
    cursor = connections['radius'].cursor()
    cursor.execute("""
        SELECT 
            voucher_number, 
            status, 
            activated_at,
            data
        FROM vouchers
    """)

    rows = cursor.fetchall()

    for voucher_number, status, activated_at, data in rows:
        try:
            voucher = Voucher.objects.select_related("offer").get(
                serial=voucher_number
            )

            if activated_at is not None:
                
                activated_at_aware = timezone.make_aware(activated_at)
                voucher.activated_at = activated_at_aware

                offer = voucher.offer

                # ---- calculate expires_at ----
                if offer.duration_type == "minutes":
                    voucher.expires_at = activated_at_aware + relativedelta(
                        minutes=offer.duration_value
                    )

                elif offer.duration_type == "hours":
                    voucher.expires_at = activated_at_aware + relativedelta(
                        hours=offer.duration_value
                    )

                elif offer.duration_type == "days":
                    voucher.expires_at = activated_at_aware + relativedelta(
                        days=offer.duration_value
                    )

                elif offer.duration_type == "months":
                    voucher.expires_at = activated_at_aware + relativedelta(
                        months=offer.duration_value
                    )

                else:
                    voucher.expires_at = None


            if status == 1:
                # ---------------------------
                # ACTIVATED
                # ---------------------------

                # ---- update usage ----
                if data:
                    data =  round(data / 1024 / 1024, 2)
                    voucher.usage_mb = data
                if voucher.expires_at < timezone.now():
                    voucher.is_used = "expired"
                else:
                    voucher.is_used = "used"

            elif status == 2:
                if data:
                    data =  round(data / 1024 / 1024, 2)
                    voucher.usage_mb = data
                voucher.is_used = "expired"
            else:
                # ---------------------------
                # NOT USED
                # ---------------------------
                voucher.is_used = "unused"
                voucher.activated_at = None
                voucher.expires_at = None

            voucher.save()

        except Voucher.DoesNotExist:
            continue

        except Exception as e:
            print(f"Error updating voucher {voucher_number}: {e}")
            continue

