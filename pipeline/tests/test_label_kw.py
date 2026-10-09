from es.label_kw import label_text

def test_narrative_variants_and_multilabel_cap():
    for text in ["loss of motive power", "lost all power", "loss of power", "power loss"]:
        assert label_text(text)["primary"] == "loss_of_power"
    for text in ["fires", "flames", "smoking", "burning smell", "overheated", "melted"]:
        assert label_text(text)["primary"] == "fire_thermal"
    assert label_text("fire electrical brake steering wheel")["secondary"] == ["electrical_failure","brakes"]
    assert label_text("unrecognized description") == {"primary":"other","secondary":[]}
