from tesela3b import config


def test_crs_metrico_es_utm_14n():
    # Todo cálculo de distancias, áreas y KDE debe hacerse en metros (EPSG:6369)
    assert config.CRS_METRIC == "EPSG:6369"


def test_area_de_estudio_cdmx():
    assert config.CVE_ENT == "09"
