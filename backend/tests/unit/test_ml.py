from unittest.mock import MagicMock


def test_hash_source_text_is_stable():
    from app.core.ml import hash_source_text

    assert hash_source_text("  hello ") == hash_source_text("hello")
    assert hash_source_text("hello") != hash_source_text("hello!")


def test_embed_text_uses_sentence_transformer(monkeypatch):
    from app.core import ml as ml_mod

    fake_model = MagicMock()
    fake_vec = MagicMock()
    fake_vec.tolist.return_value = [0.0] * 384
    fake_model.encode.return_value = [fake_vec]

    monkeypatch.setattr(ml_mod, "_load_sentence_transformer", lambda _: fake_model)

    vec = ml_mod.embed_text("hi", "sentence-transformers/all-MiniLM-L6-v2")
    assert isinstance(vec, list)
    assert len(vec) == 384
    fake_model.encode.assert_called_once()
