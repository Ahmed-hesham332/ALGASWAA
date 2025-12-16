from django.db import models

class RadCheck(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    op = models.CharField(max_length=2)
    value = models.CharField(max_length=253)

    class Meta:
        managed = False   # <-- DO NOT let Django migrate this
        db_table = 'radcheck'
        app_label = 'radius_integration'


class RadReply(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    op = models.CharField(max_length=2)
    value = models.CharField(max_length=253)

    class Meta:
        managed = False
        db_table = 'radreply'
        app_label = 'radius_integration'


class RadAcct(models.Model):
    radacctid = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64, null=True)
    acctstarttime = models.DateTimeField(null=True)
    acctstoptime = models.DateTimeField(null=True)
    framedipaddress = models.CharField(max_length=15, null=True)
    acctsessiontime = models.BigIntegerField(null=True)
    callingstationid = models.CharField(max_length=50, null=True)

    class Meta:
        managed = False
        db_table = 'radacct'
        app_label = 'radius_integration'

