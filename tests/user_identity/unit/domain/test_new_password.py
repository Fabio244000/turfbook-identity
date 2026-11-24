import pytest

from app.user_identity.domain.entities.new_password import differences


class TestDifferences:
    @pytest.mark.parametrize(
        ('first', 'second', 'expected'),
        [
            ('GrassElSol2026!', 'GrassElSol2026!', 0),
            ('GrassElSol2026!', 'grasselsol2026!', 0),
            ('GrassElSol2026!', 'GrassElSol2026!!', 1),
            ('GrassElSol2026!', 'GrassElSol2026', 1),
            ('GrassElSol2026!', 'GrassElSol2029?', 2),
            ('GrassElSol2026!', 'GrassElSol2062!', 2),
            ('GrassElSol2026!', 'GrassElLuna2026!', 4),
            ('', 'abc', 3),
        ],
    )
    def test_counts_the_characters_added_removed_or_changed(
        self, first: str, second: str, expected: int
    ) -> None:
        assert differences(first, second) == expected
