import fixtures
import pytest

import dnfile
from dnfile.resource import InternalResource, ResourceSet


def _resources_by_name(path):
    # Normalize the resource list into a name-keyed mapping for direct assertions.
    dn = dnfile.dnPE(path)

    assert dn.net is not None
    assert dn.net.resources is not None

    return dn, {str(rsrc.name): rsrc for rsrc in dn.net.resources}


def test_minimal_resource_fixture_parses():
    """Verify the minimal fixture preserves one named resource and its decoded values."""
    path = fixtures.get_data_path_by_name("minimal-res.exe")

    dn, resources = _resources_by_name(path)

    assert len(resources) == 1

    resource = resources["sample.resources"]
    assert isinstance(resource, InternalResource)
    assert str(resource.name) == "sample.resources"
    assert resource.public is True
    assert resource.private is False
    assert isinstance(resource.data, ResourceSet)

    resource_set = resource.data
    assert resource_set.struct is not None
    assert resource_set.struct.Version == 2
    assert resource_set.struct.NumberOfResources == 2
    assert [entry.name for entry in resource_set.entries] == ["Count", "Greeting"]

    count_entry = resource_set.entries[0]
    greeting_entry = resource_set.entries[1]

    assert count_entry.type_name == "System.Int32"
    assert count_entry.value == 42
    assert greeting_entry.type_name == "System.String"
    assert greeting_entry.value == "Hello"


def test_mal_resource_fixture_parses_modulo_resources():
    """Verify the malware fixture exposes the expected resource set contents."""
    path = fixtures.get_data_path_by_name("387f15043f0198fd3a637b0758c2b6dde9ead795c3ed70803426fc355731b173.dll_")
    # Skip the fixture when it is not present locally; this malware sample is optional.
    if not path.exists():
        raise pytest.xfail("test file 38741504... (DANGER: malware) not found in test fixtures")

    dn, resources = _resources_by_name(path)

    # This fixture is intentionally richer and should expose many internal resources.
    assert len(resources) == 13

    # Modulo.g.resources contains both BAML and SVG stream entries.
    resource = resources["Modulo.g.resources"]
    assert isinstance(resource, InternalResource)
    assert isinstance(resource.data, ResourceSet)

    resource_set = resource.data
    assert resource_set.struct is not None
    assert resource_set.struct.Version == 2
    assert resource_set.struct.NumberOfResources == 24
    assert resource_set.entries[0].name == "windowazulso.baml"
    assert resource_set.entries[0].type_name == "System.Stream"
    assert isinstance(resource_set.entries[0].value, bytes)
    assert resource_set.entries[1].name == "resources/logo001.svg"
    assert resource_set.entries[1].type_name == "System.Stream"
    assert resource_set.entries[1].value.startswith(b"<svg")


def test_mal_resource_fixture_parses_costura_resources():
    """Verify the malware fixture preserves empty, bitmap, and metadata resources."""
    path = fixtures.get_data_path_by_name("7f4ba9fc95b30baf8922a6933a4ff1c6a7fef41fae487bb31014c4963357770f.dll_")
    # Skip the fixture when it is not present locally; this malware sample is optional.
    if not path.exists():
        raise pytest.xfail("test file 7f4ba9fc... (DANGER: malware) not found in test fixtures")

    dn, resources = _resources_by_name(path)

    assert len(resources) == 17

    empty_resource = resources["Principal.oAkJwCmMjdhmZUeQqzIqCrdWUotYSIbbSGPVDSnNwYvKrAJsAhUNUtBRnzYyZvOqQ.resources"]
    assert isinstance(empty_resource, InternalResource)
    assert isinstance(empty_resource.data, ResourceSet)
    assert empty_resource.data.struct is not None
    assert empty_resource.data.struct.NumberOfResources == 0
    assert empty_resource.data.entries == []

    # Principal.Resources.resources is the main resource bundle to validate.
    resource = resources["Principal.Resources.resources"]
    assert isinstance(resource, InternalResource)
    assert isinstance(resource.data, ResourceSet)

    resource_set = resource.data
    assert resource_set.struct is not None
    assert resource_set.struct.Version == 2
    assert resource_set.struct.NumberOfResources == 9
    assert [entry.name for entry in resource_set.entries[:3]] == ["logo9991", "logo998", "logo341"]
    assert resource_set.entries[0].type_name == "System.Drawing.Bitmap"
    assert resource_set.entries[0].value is None

    compressed_resource = resources["costura.metadata"]
    assert isinstance(compressed_resource.data, bytes)
    assert len(compressed_resource.data) > 0
