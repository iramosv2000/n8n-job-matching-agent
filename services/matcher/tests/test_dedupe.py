from matcher.dedupe import find_duplicates, jaccard, title_words
from matcher.models import DedupeItem, DedupeRequest


def item(offer_id, title, company="Andes Procesos SpA", region="Antofagasta"):
    return DedupeItem(offer_id=offer_id, title=title, company=company, region=region)


def test_title_words_drop_stopwords_and_accents():
    assert title_words("Ingeniero de Automatización y Control") == {"ingeniero", "automatizacion", "control"}
    assert jaccard(set(), set()) == 0.0


def test_links_candidate_to_existing_offer():
    request = DedupeRequest(
        candidates=[item("trabajando:9", "Ingeniero(a) de Automatización Control")],
        existing=[item("getonbrd:1", "Ingeniero/a de Automatización y Control")],
    )
    [link] = find_duplicates(request).links
    assert (link.offer_id, link.duplicate_of) == ("trabajando:9", "getonbrd:1")
    assert link.similarity >= 0.7


def test_links_later_candidate_to_earlier_candidate():
    request = DedupeRequest(
        candidates=[item("a:1", "Ingeniero Procesos con IA"), item("b:2", "Ingeniero Procesos IA")]
    )
    [link] = find_duplicates(request).links
    assert (link.offer_id, link.duplicate_of) == ("b:2", "a:1")


def test_no_link_across_regions_companies_or_dissimilar_titles():
    request = DedupeRequest(
        candidates=[
            item("a:1", "Ingeniero de Automatización", region="Metropolitana"),
            item("a:2", "Ingeniero de Automatización", company="Otra Empresa"),
            item("a:3", "Técnico Electricista Mantención"),
        ],
        existing=[item("e:1", "Ingeniero de Automatización")],
    )
    assert find_duplicates(request).links == []


def test_anonymous_companies_and_self_matches_are_skipped():
    request = DedupeRequest(
        candidates=[
            item("a:1", "Ingeniero de Automatización", company="Empresa Confidencial"),
            item("e:1", "Ingeniero de Automatización"),
            item("a:4", "Ingeniero", company=None),
        ],
        existing=[item("e:1", "Ingeniero de Automatización")],
    )
    assert find_duplicates(request).links == []


def test_best_match_wins():
    request = DedupeRequest(
        candidates=[item("c:1", "Ingeniero Automatización Control Procesos")],
        existing=[
            item("e:1", "Ingeniero Automatización Control Procesos Planta"),
            item("e:2", "Ingeniero Automatización Control Procesos"),
        ],
    )
    [link] = find_duplicates(request).links
    assert link.duplicate_of == "e:2"
    assert link.similarity == 1.0
