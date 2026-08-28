from django.db import models

class Observation(models.Model):
    id = models.AutoField(primary_key=True)
    dataset_id = models.CharField(max_length=100, db_index=True)
    category = models.CharField(max_length=100, db_index=True)
    entity_name = models.CharField(max_length=255)
    variable_name = models.CharField(max_length=255)
    year = models.IntegerField(null=True, blank=True, db_index=True)
    period = models.CharField(max_length=50, null=True, blank=True)
    value = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False  # Django will not manage table creation/deletion
        db_table = 'observations'
        ordering = ['-id']

    def __str__(self):
        return f"[{self.category}] {self.entity_name} - {self.variable_name} ({self.year}): {self.value}"
