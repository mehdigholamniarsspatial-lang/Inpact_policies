"""Database models for the Ireland core climate-policy dataset.

The main analytical grain of the release is policy_id + sector + year.
`PolicySeries` stores the attributes that are constant for a policy-sector
slice, and `PolicyYear` stores the annual values (status, implementation,
CAPMF stringency and the composite intensity indices).
"""
from django.db import models


class PolicySeries(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    policy_id = models.CharField(max_length=40, db_index=True)
    policy_name = models.CharField(max_length=255)
    sector = models.CharField(max_length=30, db_index=True)
    layer = models.CharField(max_length=40, db_index=True)
    bundle = models.CharField(max_length=80)
    mechanism = models.CharField(max_length=40, db_index=True)
    mechanism_class = models.CharField(max_length=40)
    regime = models.CharField(max_length=20)
    instrument_type = models.CharField(max_length=60)
    ghg_affected = models.CharField(max_length=40)
    source_datasets = models.CharField(max_length=20)
    eea_pam_ids = models.CharField(max_length=120, blank=True)
    all_eea_variant_ids = models.CharField(max_length=200, blank=True)
    prior_policy_ids = models.CharField(max_length=400, blank=True)
    capmf_code = models.CharField(max_length=200, blank=True)
    match_confidence = models.CharField(max_length=20)
    capmf_match_scope = models.CharField(max_length=40)
    selection_rule = models.CharField(max_length=30)
    materiality_group_flag = models.BooleanField(default=False)
    anchor_flag = models.BooleanField(default=False)
    multi_sector_flag = models.BooleanField(default=False)
    sector_effect_rank = models.FloatField(null=True, blank=True)
    reported_effect_kt = models.FloatField(null=True, blank=True)
    effect_source = models.CharField(max_length=40, blank=True)
    effect_reference_year = models.IntegerField(null=True, blank=True)
    effect_value_state = models.CharField(max_length=40, blank=True)
    materiality_sector = models.CharField(max_length=30, blank=True)
    start_year = models.IntegerField()
    end_year = models.IntegerField(null=True, blank=True)
    start_year_basis = models.TextField(blank=True)
    legacy = models.CharField(max_length=30, blank=True)
    coverage_share = models.FloatField(null=True, blank=True)
    coverage_rationale = models.TextField(blank=True)
    bindingness = models.FloatField(null=True, blank=True)
    bindingness_rationale = models.TextField(blank=True)
    source_citation = models.TextField(blank=True)
    aggregation_role = models.CharField(max_length=80)
    member_policy_ids = models.TextField(blank=True)
    score_family_id = models.CharField(max_length=200, blank=True)
    lag_years = models.FloatField(null=True, blank=True)
    ramp_years = models.FloatField(null=True, blank=True)
    half_life_years = models.FloatField(null=True, blank=True)
    parameter_basis = models.TextField(blank=True)
    eligible_member_count = models.IntegerField(default=1)
    data_quality_flags = models.TextField(blank=True)  # union across years
    description = models.TextField(blank=True)          # EEA description / anchor basis
    reference_url = models.URLField(max_length=500, blank=True)
    # handy pre-computed summaries (filled by the loader)
    peak_intensity = models.FloatField(null=True, blank=True)
    intensity_2023 = models.FloatField(null=True, blank=True)
    capmf_years = models.IntegerField(default=0)
    assumed_years = models.IntegerField(default=0)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "sector", "start_year", "policy_name"]
        verbose_name_plural = "policy series"

    def __str__(self):
        return f"{self.policy_name} [{self.sector}]"

    @property
    def is_residual(self):
        return self.layer == "residual"


class PolicyYear(models.Model):
    series = models.ForeignKey(PolicySeries, on_delete=models.CASCADE, related_name="years")
    year = models.IntegerField(db_index=True)
    status_in_year = models.CharField(max_length=40)
    years_since_start = models.IntegerField()
    implementation_source = models.CharField(max_length=30)
    implementation_level = models.FloatField(null=True, blank=True)
    capmf_stringency = models.FloatField(null=True, blank=True)
    intensity_index = models.FloatField(null=True, blank=True)
    intensity_index_equal = models.FloatField(null=True, blank=True)
    intensity_index_equal_gated = models.FloatField(null=True, blank=True)
    temporal_weight = models.FloatField(null=True, blank=True)
    implementation_detail = models.CharField(max_length=120, blank=True)
    capmf_observation_status = models.CharField(max_length=40, blank=True)
    data_quality_flag = models.TextField(blank=True)

    class Meta:
        ordering = ["series", "year"]
        unique_together = ("series", "year")


class SelectionCandidate(models.Model):
    candidate_id = models.CharField(max_length=40, unique=True)
    candidate_origin = models.CharField(max_length=40)
    candidate_name = models.CharField(max_length=300)
    source_pam_ids = models.CharField(max_length=120, blank=True)
    eligible = models.BooleanField(default=False)
    criteria_a_mitigation = models.BooleanField(default=False)
    criteria_b_ireland = models.BooleanField(default=False)
    criteria_c_instrument = models.BooleanField(default=False)
    criteria_d_start = models.BooleanField(default=False)
    criteria_e_active = models.BooleanField(default=False)
    exclusion_reason = models.TextField(blank=True)
    selection_rule = models.CharField(max_length=40, blank=True)
    materiality_group_flag = models.BooleanField(default=False)
    anchor_flag = models.BooleanField(default=False)
    primary_sector = models.CharField(max_length=30, blank=True)
    reported_effect_kt = models.FloatField(null=True, blank=True)
    effect_source = models.CharField(max_length=40, blank=True)
    sector_effect_rank = models.FloatField(null=True, blank=True)
    cumulative_effect_share = models.FloatField(null=True, blank=True)
    selected_start_year = models.IntegerField(null=True, blank=True)
    reported_end_year = models.IntegerField(null=True, blank=True)
    output_policy_ids = models.CharField(max_length=300, blank=True)
    decision_basis = models.TextField(blank=True)
    outcome = models.CharField(max_length=20)  # core / residual / excluded

    class Meta:
        ordering = ["candidate_origin", "candidate_id"]


class ResidualMember(models.Model):
    residual_sector = models.CharField(max_length=30, db_index=True)
    policy_id = models.CharField(max_length=40)
    policy_name = models.CharField(max_length=255)
    mechanism = models.CharField(max_length=40)
    layer = models.CharField(max_length=40)
    start_year = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True)
    reported_effect_kt = models.FloatField(null=True, blank=True)
    coverage_share = models.FloatField(null=True, blank=True)
    bindingness = models.FloatField(null=True, blank=True)
    intensity_2023 = models.FloatField(null=True, blank=True)


class OverlapRelation(models.Model):
    parent_id = models.CharField(max_length=40)
    related_id = models.CharField(max_length=40)
    relationship = models.CharField(max_length=60)
    treatment = models.TextField()


class SectorMateriality(models.Model):
    sector = models.CharField(max_length=30, unique=True)
    eligible_pam_units = models.IntegerField()
    positive_quantified_units = models.IntegerField()
    materiality_units = models.IntegerField()
    ranking_total_kt = models.FloatField(null=True, blank=True)
    selected_ranking_kt = models.FloatField(null=True, blank=True)
    achieved_share = models.FloatField(null=True, blank=True)
    assessment = models.CharField(max_length=40)
    interpretation = models.TextField(blank=True)


class Reference(models.Model):
    source_id = models.CharField(max_length=40, unique=True)
    publisher = models.CharField(max_length=200)
    title = models.CharField(max_length=400)
    publication_date = models.CharField(max_length=60, blank=True)
    url = models.URLField(max_length=600, blank=True)
    locator = models.TextField(blank=True)
    access_status = models.CharField(max_length=60, blank=True)


class ValidationCheck(models.Model):
    check_name = models.CharField(max_length=80)
    result = models.CharField(max_length=20)
    detail = models.TextField()


class ReconciliationEntry(models.Model):
    topic = models.CharField(max_length=80)
    issue = models.TextField()
    decision = models.TextField()
    locator = models.CharField(max_length=200, blank=True)


class DictionaryField(models.Model):
    position = models.IntegerField()
    column = models.CharField(max_length=60)
    unit = models.CharField(max_length=60)
    definition = models.TextField()

    class Meta:
        ordering = ["position"]


class CapmfCategory(models.Model):
    code = models.CharField(max_length=40, unique=True)
    label = models.CharField(max_length=200)
    level = models.IntegerField()
    domain = models.CharField(max_length=60, blank=True)
    instrument_class = models.CharField(max_length=60, blank=True)
    first_positive_year = models.IntegerField(null=True, blank=True)
    eligible = models.BooleanField(null=True)
    exclusion_reason = models.TextField(blank=True)
    represented_by = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["level", "code"]


class CapmfObservation(models.Model):
    category = models.ForeignKey(CapmfCategory, on_delete=models.CASCADE, related_name="observations")
    measure = models.CharField(max_length=20)  # POL_STRINGENCY / POL_COUNT
    year = models.IntegerField()
    value = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=2)

    class Meta:
        ordering = ["category", "year"]


class EeaPam(models.Model):
    pam_id = models.IntegerField(unique=True)
    policy_id = models.CharField(max_length=40, blank=True)
    name = models.CharField(max_length=400)
    scenario = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=60, blank=True)
    start = models.CharField(max_length=20, blank=True)
    finish = models.CharField(max_length=20, blank=True)
    instrument_type = models.CharField(max_length=200, blank=True)
    sectors = models.CharField(max_length=300, blank=True)
    ghgs = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    expost_kt = models.FloatField(null=True, blank=True)
    wem_2030_kt = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["pam_id"]
