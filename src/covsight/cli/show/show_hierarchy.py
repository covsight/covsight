"""
Show Hierarchy Command

The instance tree with every scope's type and the covered/total bins in its
subtree.  Ignore and illegal bins are not counted.
"""
from typing import Any, Dict, List, Optional, TextIO

from covsight.cli.show_base import ShowBase


class ShowHierarchy(ShowBase):

    def get_data(self) -> Dict[str, Any]:
        from covsight.core.api import ScopeTypeT

        tops = list(self.db.scopes(ScopeTypeT.ALL))
        roots = [s for s in tops if s.getScopeType() == ScopeTypeT.INSTANCE] or tops
        hierarchy = [self._traverse_scope(s, 0)[0] for s in roots]
        return {
            "database": self.args.db,
            "hierarchy": hierarchy,
            "summary": {"total_scopes": self._count_scopes(hierarchy)},
        }

    def _traverse_scope(self, scope, depth: int):
        """Returns (node or None when beyond max depth, covered, total)."""
        from covsight.core.api import CoverTypeT, ScopeTypeT

        covered = total = 0
        for ci in scope.coverItems(CoverTypeT.ALL):
            cd = ci.getCoverData()
            if cd.type in (CoverTypeT.IGNOREBIN, CoverTypeT.ILLEGALBIN):
                continue
            total += 1
            covered += cd.data >= max(cd.at_least or 0, 1)

        max_depth = getattr(self.args, "max_depth", None)
        children: List[Dict[str, Any]] = []
        for child in scope.scopes(ScopeTypeT.ALL):
            node, c, t = self._traverse_scope(child, depth + 1)
            covered += c
            total += t
            if node is not None:
                children.append(node)

        if max_depth is not None and depth >= max_depth:
            return None, covered, total
        node: Dict[str, Any] = {
            "name": scope.getScopeName(),
            "type": self._get_scope_type_name(scope.getScopeType()),
            "depth": depth,
        }
        if total:
            node["covered"] = covered
            node["total"] = total
            node["coverage"] = round(100.0 * covered / total, 2)
        if children:
            node["children"] = children
            node["child_count"] = len(children)
        return node, covered, total

    @staticmethod
    def _get_scope_type_name(scope_type) -> str:
        from covsight.core.api import ScopeTypeT
        try:
            return ScopeTypeT(scope_type).name.lower()
        except ValueError:
            return "unknown_%#x" % int(scope_type)

    def _count_scopes(self, hierarchy: List[Dict[str, Any]]) -> int:
        count = len(hierarchy)
        for item in hierarchy:
            if "children" in item:
                count += self._count_scopes(item["children"])
        return count

    def _write_text(self, data: Dict[str, Any], fp: TextIO):
        def emit(node, indent):
            cov = ""
            if "total" in node:
                cov = "  %.2f%% (%d/%d)" % (node["coverage"], node["covered"], node["total"])
            fp.write("%s%s [%s]%s\n" % ("  " * indent, node["name"], node["type"], cov))
            for c in node.get("children", []):
                emit(c, indent + 1)
        for node in data["hierarchy"]:
            emit(node, 0)
