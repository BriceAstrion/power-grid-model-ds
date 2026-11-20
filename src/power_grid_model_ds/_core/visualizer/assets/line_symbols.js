// SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
//
// SPDX-License-Identifier: MPL-2.0

/*
 * Render electrical Lines as two parallel strokes.
 * The original Cytoscape edge remains responsible for graph interaction.
 *
 * Dash Cytoscape 1.0.2 exposes its instance through window.cy.
 * This is an undocumented integration point.
 */
(() => {
    "use strict";

    const SVG_NS = "http://www.w3.org/2000/svg";
    const OFFSET = 9;
    const STROKE_WIDTH = 5;
    const OVERLAY_ID = "pgm-line-symbols";

    const NON_LINE_CLASSES = [
        "link",
        "transformer",
        "generic_branch",
        "asym_line"
    ];

    let activeCy = null;
    let cleanup = null;

    function isLine(edge) {
        return edge.isEdge() &&
            edge.hasClass("branch") &&
            !NON_LINE_CLASSES.some(name => edge.hasClass(name));
    }

    function isClosed(edge) {
        return ![
            "open_branch",
            "open_branch_from",
            "open_branch_to"
        ].some(name => edge.hasClass(name));
    }

    function createStroke(svg, x1, y1, x2, y2, color, width) {
        const line = document.createElementNS(SVG_NS, "line");

        line.setAttribute("x1", x1);
        line.setAttribute("y1", y1);
        line.setAttribute("x2", x2);
        line.setAttribute("y2", y2);
        line.setAttribute("stroke", color);
        line.setAttribute("stroke-width", width);

        svg.appendChild(line);
    }

    function drawLine(svg, edge, cy, color) {
        const sourceNode = edge.source();
        const targetNode = edge.target();

        const source = sourceNode.renderedPosition();
        const target = targetNode.renderedPosition();

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const length = Math.hypot(dx, dy);

        if (!length) return;

        const ux = dx / length;
        const uy = dy / length;
        const nx = -uy;
        const ny = ux;

        const zoom = cy.zoom();
        const offset = OFFSET * zoom;
        const width = STROKE_WIDTH * zoom;

        const sourceRadius = Math.min(
            sourceNode.renderedWidth(),
            sourceNode.renderedHeight()
        ) / 2;

        const targetRadius = Math.min(
            targetNode.renderedWidth(),
            targetNode.renderedHeight()
        ) / 2;

        if (offset >= sourceRadius || offset >= targetRadius) {
            return;
        }

        const sourceInset = Math.sqrt(
            sourceRadius ** 2 - offset ** 2
        );

        const targetInset = Math.sqrt(
            targetRadius ** 2 - offset ** 2
        );

        for (const side of [-1, 1]) {
            createStroke(
                svg,
                source.x + ux * sourceInset + nx * offset * side,
                source.y + uy * sourceInset + ny * offset * side,
                target.x - ux * targetInset + nx * offset * side,
                target.y - uy * targetInset + ny * offset * side,
                color,
                width
            );
        }
    }

    function install(cy) {
        const container = cy.container();

        if (!container) return null;

        const svg = document.createElementNS(SVG_NS, "svg");
        svg.id = OVERLAY_ID;
        svg.style.cssText = [
            "position:absolute",
            "inset:0",
            "width:100%",
            "height:100%",
            "pointer-events:none",
            "z-index:10"
        ].join(";");

        container.style.position = "relative";
        container.appendChild(svg);

        const managedEdges = new Map();
        let frame = null;
        let selectedLineOnPointerDown = null;

        function restoreEdge(edge) {
            if (!managedEdges.has(edge.id())) return;

            const original = managedEdges.get(edge.id());

            edge.style({
                "line-opacity": original.lineOpacity,
                "target-arrow-shape": original.targetArrowShape,
                "source-arrow-shape": original.sourceArrowShape
            });

            managedEdges.delete(edge.id());
        }

        function manageEdge(edge) {
            if (managedEdges.has(edge.id())) return;

            managedEdges.set(edge.id(), {
                lineOpacity: edge.pstyle("line-opacity").value,
                targetArrowShape: edge.pstyle("target-arrow-shape").value,
                sourceArrowShape: edge.pstyle("source-arrow-shape").value
            });

            edge.style({
                "line-opacity": 0,
                "target-arrow-shape": "none",
                "source-arrow-shape": "none"
            });
        }

        function update() {
            frame = null;

            if (cy.destroyed()) return;

            svg.setAttribute(
                "viewBox",
                `0 0 ${container.clientWidth} ${container.clientHeight}`
            );

            svg.replaceChildren();

            const activeIds = new Set();

            cy.edges().forEach(edge => {
                if (!isLine(edge) || !isClosed(edge)) {
                    restoreEdge(edge);
                    return;
                }

                activeIds.add(edge.id());

                const color = edge.pstyle("line-color").strValue;

                manageEdge(edge);
                drawLine(svg, edge, cy, color);
            });

            for (const id of managedEdges.keys()) {
                if (!activeIds.has(id)) {
                    const edge = cy.getElementById(id);

                    if (edge.length) {
                        restoreEdge(edge);
                    } else {
                        managedEdges.delete(id);
                    }
                }
            }
        }

        function scheduleUpdate() {
            if (frame !== null) return;
            frame = requestAnimationFrame(update);
        }

        function deselectOnBackgroundTap(event) {
            if (event.target === cy) {
                cy.$(":selected").unselect();
            }
        }

        function rememberSelectedLine(event) {
            const edge = event.target;

            selectedLineOnPointerDown = isLine(edge) &&
                isClosed(edge) &&
                edge.selected()
                ? edge.id()
                : null;
        }

        function toggleSelectedLine(event) {
            const edge = event.target;

            if (
                selectedLineOnPointerDown === edge.id() &&
                edge.selected()
            ) {
                edge.unselect();
            }

            selectedLineOnPointerDown = null;
        }

        function clearPendingSelection() {
            selectedLineOnPointerDown = null;
        }

        cy.on("mousedown touchstart", "edge", rememberSelectedLine);
        cy.on("tap", "edge", toggleSelectedLine);
        cy.on("drag", clearPendingSelection);
        cy.on("pan", clearPendingSelection);

        cy.on("pan zoom position add remove select unselect", scheduleUpdate);
        cy.on("tap", deselectOnBackgroundTap);

        scheduleUpdate();

        return () => {
            cy.off("mousedown touchstart", "edge", rememberSelectedLine);
            cy.off("tap", "edge", toggleSelectedLine);
            cy.off("drag", clearPendingSelection);
            cy.off("pan", clearPendingSelection);

            cy.off("pan zoom position add remove select unselect", scheduleUpdate);
            cy.off("tap", deselectOnBackgroundTap);

            if (frame !== null) {
                cancelAnimationFrame(frame);
            }

            for (const id of managedEdges.keys()) {
                const edge = cy.getElementById(id);

                if (edge.length) {
                    restoreEdge(edge);
                }
            }

            svg.remove();
        };
    }

    const observer = setInterval(() => {
        const cy = window.cy;

        if (!cy || typeof cy.edges !== "function" || cy.destroyed()) {
            if (cleanup) cleanup();

            cleanup = null;
            activeCy = null;
            return;
        }

        if (cy === activeCy) return;

        if (cleanup) cleanup();

        activeCy = cy;
        cleanup = install(cy);
    }, 500);

    window.addEventListener("beforeunload", () => {
        clearInterval(observer);

        if (cleanup) cleanup();
    });
})();
