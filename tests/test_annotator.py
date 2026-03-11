"""Tests for annotator — Claude API pattern classification."""

import json
from unittest.mock import MagicMock, patch

import pytest

from services.annotator import _strip_fences, annotate_mistake


class TestStripFences:
    def test_plain_json(self):
        assert _strip_fences('{"a": 1}') == '{"a": 1}'

    def test_json_code_fence(self):
        text = '```json\n{"a": 1}\n```'
        assert _strip_fences(text) == '{"a": 1}'

    def test_plain_code_fence(self):
        text = '```\n{"a": 1}\n```'
        assert _strip_fences(text) == '{"a": 1}'


class TestAnnotateMistake:
    @pytest.mark.asyncio
    @patch("services.annotator._get_client")
    async def test_valid_response(self, mock_get_client):
        """Annotator returns correct pattern ID and annotation."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_json = {
            "registry_pattern_id": "MT-001",
            "annotation": "Missed a knight fork on f7 targeting king and rook.",
        }
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(response_json))]
        mock_client.messages.create.return_value = mock_message

        result = await annotate_mistake(
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            played_move_san="Bc4",
            best_move_san="Nxf7",
            cp_loss=250.0,
            phase="middlegame",
            candidate_patterns=[
                {"id": "MT-001", "name": "Missed Fork", "description": "Failed to see a fork"},
                {"id": "MT-002", "name": "Missed Pin", "description": "Failed to see a pin"},
            ],
        )

        assert result["registry_pattern_id"] == "MT-001"
        assert "fork" in result["annotation"].lower()

    @pytest.mark.asyncio
    @patch("services.annotator._get_client")
    async def test_code_fence_response(self, mock_get_client):
        """Annotator handles markdown-fenced JSON responses."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_text = '```json\n{"registry_pattern_id": "MS-001", "annotation": "Test"}\n```'
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=response_text)]
        mock_client.messages.create.return_value = mock_message

        result = await annotate_mistake(
            fen="test", played_move_san="e4", best_move_san="d4",
            cp_loss=80.0, phase="middlegame",
            candidate_patterns=[
                {"id": "MS-001", "name": "Passive Piece", "description": "test"},
            ],
        )
        assert result["registry_pattern_id"] == "MS-001"

    @pytest.mark.asyncio
    @patch("services.annotator._get_client")
    async def test_unclassified_fallback(self, mock_get_client):
        """Returns UNCLASSIFIED after two failures."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Both calls return invalid JSON
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="not json at all")]
        mock_client.messages.create.return_value = mock_message

        result = await annotate_mistake(
            fen="test", played_move_san="e4", best_move_san="d4",
            cp_loss=100.0, phase="opening",
            candidate_patterns=[
                {"id": "OT-001", "name": "Test", "description": "test"},
            ],
        )
        assert result["registry_pattern_id"] == "UNCLASSIFIED"
        assert result["annotation"] == "Classification failed"
        # Two calls: first attempt + retry
        assert mock_client.messages.create.call_count == 2
