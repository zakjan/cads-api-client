from cads_api_client import processing


def test_processes(dev_env_api_url: str) -> None:
    proc = processing.Processing(f"{dev_env_api_url}/retrieve")

    res = proc.processes()

    assert isinstance(res, processing.ProcessList)
    assert "processes" in res.json
    assert isinstance(res.json["processes"], list)
    assert "links" in res.json
    assert isinstance(res.json["links"], list)

    expected_process_id = "reanalysis-era5-land-monthly-means"

    assert expected_process_id in res.process_ids()


def test_process(dev_env_api_url: str) -> None:
    process_id = "reanalysis-era5-land-monthly-means"
    proc = processing.Processing(f"{dev_env_api_url}/retrieve")

    res = proc.process(process_id)

    assert isinstance(res, processing.Process)
    assert res.id == process_id
    assert "links" in res.json
    assert isinstance(res.json["links"], list)
