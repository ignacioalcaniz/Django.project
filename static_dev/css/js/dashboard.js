document.addEventListener("DOMContentLoaded", function () {
    const filterButtons = document.querySelectorAll(".market-filter-btn");
    const assetCards = document.querySelectorAll(".market-panel .asset-card");
    const resultCounter = document.querySelector(".market-results-counter");
    const searchInput = document.querySelector("#assetSearchInput");

    function normalizeText(value) {
        return (value || "").toString().toLowerCase().trim();
    }

    function getJsonData(elementId) {
        const element = document.getElementById(elementId);

        if (!element) {
            return [];
        }

        try {
            return JSON.parse(element.textContent);
        } catch (error) {
            console.error(`Error leyendo datos de ${elementId}:`, error);
            return [];
        }
    }

    function animateDashboard() {
        if (typeof gsap === "undefined") return;

        gsap.from(".portfolio-executive", {
            opacity: 0,
            y: 28,
            duration: 0.7,
            ease: "power3.out"
        });

        gsap.from(".summary-card", {
            opacity: 0,
            y: 20,
            duration: 0.55,
            stagger: 0.08,
            delay: 0.15,
            ease: "power3.out"
        });

        gsap.from(".panel", {
            opacity: 0,
            y: 22,
            duration: 0.6,
            stagger: 0.08,
            delay: 0.25,
            ease: "power3.out"
        });
    }

    function animateVisibleCards() {
        if (typeof gsap === "undefined") return;

        const visibleCards = document.querySelectorAll(".market-panel .asset-card:not(.asset-hidden)");

        gsap.fromTo(
            visibleCards,
            { opacity: 0, y: 14, scale: 0.98 },
            {
                opacity: 1,
                y: 0,
                scale: 1,
                duration: 0.35,
                stagger: 0.04,
                ease: "power2.out"
            }
        );
    }

    function applyFilters() {
        const activeButton = document.querySelector(".market-filter-btn.active");

        const filterType = activeButton ? activeButton.dataset.filterType : "all";
        const filterValue = activeButton ? activeButton.dataset.filterValue : "all";
        const searchValue = searchInput ? normalizeText(searchInput.value) : "";

        let visibleCount = 0;

        assetCards.forEach(function (card) {
            const recommendation = normalizeText(card.dataset.recommendation);
            const risk = normalizeText(card.dataset.risk);
            const symbol = normalizeText(card.dataset.symbol);
            const name = normalizeText(card.dataset.name);
            const fullText = normalizeText(card.innerText);

            let matchesFilter = true;

            if (filterType === "recommendation") {
                matchesFilter = recommendation === filterValue;
            }

            if (filterType === "risk") {
                matchesFilter = risk === filterValue;
            }

            const matchesSearch =
                searchValue === "" ||
                symbol.includes(searchValue) ||
                name.includes(searchValue) ||
                fullText.includes(searchValue);

            if (matchesFilter && matchesSearch) {
                card.classList.remove("asset-hidden");
                visibleCount++;
            } else {
                card.classList.add("asset-hidden");
            }
        });

        if (resultCounter) {
            resultCounter.textContent = `${visibleCount} activo/s encontrados`;
        }

        animateVisibleCards();
    }

    function setupMarketFilters() {
        filterButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                filterButtons.forEach(function (btn) {
                    btn.classList.remove("active");
                });

                button.classList.add("active");
                applyFilters();
            });
        });

        if (searchInput) {
            searchInput.addEventListener("input", applyFilters);
        }

        applyFilters();
    }

    function createPortfolioCharts() {
        if (typeof Chart === "undefined") return;

        const labels = getJsonData("portfolioLabelsData");
        const values = getJsonData("portfolioValuesData");
        const returns = getJsonData("portfolioReturnsData");
        const scores = getJsonData("portfolioScoresData");

        if (!labels.length) return;

        Chart.defaults.color = "#cbd5e1";
        Chart.defaults.borderColor = "rgba(148, 163, 184, 0.18)";
        Chart.defaults.font.family = "Arial, sans-serif";

        const distributionCanvas = document.getElementById("portfolioDistributionChart");
        const returnsCanvas = document.getElementById("portfolioReturnsChart");
        const scoresCanvas = document.getElementById("portfolioScoresChart");

        if (distributionCanvas) {
            new Chart(distributionCanvas, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        borderWidth: 2,
                        borderColor: "#0f172a",
                        backgroundColor: [
                            "rgba(56, 189, 248, 0.85)",
                            "rgba(34, 197, 94, 0.85)",
                            "rgba(245, 158, 11, 0.85)",
                            "rgba(168, 85, 247, 0.85)",
                            "rgba(239, 68, 68, 0.85)",
                            "rgba(14, 165, 233, 0.85)",
                            "rgba(132, 204, 22, 0.85)"
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "62%",
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                padding: 16,
                                usePointStyle: true
                            }
                        }
                    }
                }
            });
        }

        if (returnsCanvas) {
            new Chart(returnsCanvas, {
                type: "bar",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Rentabilidad %",
                        data: returns,
                        borderRadius: 10,
                        backgroundColor: returns.map(function (value) {
                            return value >= 0
                                ? "rgba(34, 197, 94, 0.85)"
                                : "rgba(239, 68, 68, 0.85)";
                        })
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            ticks: {
                                callback: function (value) {
                                    return value + "%";
                                }
                            }
                        }
                    }
                }
            });
        }

        if (scoresCanvas) {
            new Chart(scoresCanvas, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Score QuantEdge",
                        data: scores,
                        tension: 0.35,
                        fill: true,
                        borderWidth: 3,
                        borderColor: "rgba(56, 189, 248, 1)",
                        backgroundColor: "rgba(56, 189, 248, 0.12)",
                        pointBackgroundColor: "rgba(34, 197, 94, 1)",
                        pointBorderColor: "#020617",
                        pointBorderWidth: 2,
                        pointRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            min: 0,
                            max: 100
                        }
                    }
                }
            });
        }
    }

    animateDashboard();
    setupMarketFilters();
    createPortfolioCharts();
});