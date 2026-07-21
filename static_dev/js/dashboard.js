document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const marketElements = {
        grid: document.getElementById("assetsGrid"),
        searchInput: document.getElementById("assetSearchInput"),
        filterButtons: document.querySelectorAll(".market-filter-btn"),
        resultCounter: document.getElementById("marketResultsCounter"),
        loader: document.getElementById("marketLoader"),
        errorBox: document.getElementById("marketError"),
        retryButton: document.getElementById("marketRetryButton")
    };

    const marketState = {
        search: "",
        recommendation: "",
        risk: "",
        controller: null,
        debounceTimer: null,
        lastRequestUrl: ""
    };

    function getJsonData(elementId) {
        const element = document.getElementById(elementId);

        if (!element) {
            return [];
        }

        try {
            return JSON.parse(element.textContent);
        } catch (error) {
            console.error(
                `No se pudieron leer los datos de ${elementId}:`,
                error
            );

            return [];
        }
    }

    function registerGsapPlugins() {
        if (
            typeof gsap !== "undefined" &&
            typeof ScrollTrigger !== "undefined"
        ) {
            gsap.registerPlugin(ScrollTrigger);
        }
    }

    function userPrefersReducedMotion() {
        return window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;
    }

    function createIntroTimeline() {
        if (
            typeof gsap === "undefined" ||
            userPrefersReducedMotion()
        ) {
            return;
        }

        const timeline = gsap.timeline({
            defaults: {
                ease: "power3.out"
            }
        });

        timeline
            .from(".welcome > div:first-child", {
                opacity: 0,
                x: -28,
                duration: 0.6
            })
            .from(
                ".admin-card",
                {
                    opacity: 0,
                    x: 28,
                    duration: 0.55
                },
                "-=0.4"
            )
            .from(
                ".portfolio-executive-main > *",
                {
                    opacity: 0,
                    y: 20,
                    stagger: 0.08,
                    duration: 0.45
                },
                "-=0.2"
            )
            .from(
                ".executive-card",
                {
                    opacity: 0,
                    y: 24,
                    scale: 0.97,
                    stagger: 0.07,
                    duration: 0.45
                },
                "-=0.25"
            )
            .from(
                ".best-asset-card",
                {
                    opacity: 0,
                    y: 18,
                    duration: 0.45
                },
                "-=0.2"
            );
    }

    function createScrollAnimations() {
        if (
            typeof gsap === "undefined" ||
            typeof ScrollTrigger === "undefined" ||
            userPrefersReducedMotion()
        ) {
            return;
        }

        const sections = document.querySelectorAll(
            ".gsap-scroll-section"
        );

        sections.forEach(function (section) {
            gsap.from(section, {
                opacity: 0,
                y: 42,
                duration: 0.75,
                ease: "power3.out",
                scrollTrigger: {
                    trigger: section,
                    start: "top 86%",
                    toggleActions: "play none none none",
                    once: true
                }
            });
        });

        gsap.utils.toArray(".chart-card").forEach(function (card, index) {
            gsap.from(card, {
                opacity: 0,
                y: 30,
                scale: 0.97,
                duration: 0.65,
                delay: index * 0.08,
                ease: "power2.out",
                scrollTrigger: {
                    trigger: card,
                    start: "top 88%",
                    toggleActions: "play none none none",
                    once: true
                }
            });
        });

        gsap.utils.toArray(".watch-card").forEach(function (card, index) {
            gsap.from(card, {
                opacity: 0,
                y: 26,
                duration: 0.55,
                delay: index * 0.05,
                ease: "power2.out",
                scrollTrigger: {
                    trigger: card,
                    start: "top 90%",
                    toggleActions: "play none none none",
                    once: true
                }
            });
        });

        gsap.utils.toArray(".portfolio-card").forEach(function (card, index) {
            gsap.from(card, {
                opacity: 0,
                x: index % 2 === 0 ? -24 : 24,
                duration: 0.6,
                ease: "power2.out",
                scrollTrigger: {
                    trigger: card,
                    start: "top 88%",
                    toggleActions: "play none none none",
                    once: true
                }
            });
        });
    }

    function animateLoadedAssetCards() {
        if (
            typeof gsap === "undefined" ||
            !marketElements.grid ||
            userPrefersReducedMotion()
        ) {
            return;
        }

        const cards = marketElements.grid.querySelectorAll(
            ".asset-card"
        );

        if (!cards.length) {
            return;
        }

        gsap.fromTo(
            cards,
            {
                opacity: 0,
                y: 18,
                scale: 0.98
            },
            {
                opacity: 1,
                y: 0,
                scale: 1,
                duration: 0.4,
                stagger: 0.05,
                ease: "power2.out",
                clearProps: "transform"
            }
        );
    }

    function setMarketLoading(isLoading) {
        if (marketElements.loader) {
            marketElements.loader.hidden = !isLoading;
        }

        if (marketElements.grid) {
            marketElements.grid.setAttribute(
                "aria-busy",
                isLoading ? "true" : "false"
            );

            marketElements.grid.classList.toggle(
                "is-loading",
                isLoading
            );
        }

        if (marketElements.searchInput) {
            marketElements.searchInput.disabled = isLoading;
        }

        marketElements.filterButtons.forEach(function (button) {
            button.disabled = isLoading;
        });
    }

    function hideMarketError() {
        if (marketElements.errorBox) {
            marketElements.errorBox.hidden = true;
        }
    }

    function showMarketError() {
        if (marketElements.errorBox) {
            marketElements.errorBox.hidden = false;
        }
    }

    function updateResultCounter(count) {
        if (!marketElements.resultCounter) {
            return;
        }

        const label = count === 1 ? "activo encontrado" : "activos encontrados";

        marketElements.resultCounter.textContent =
            `${count} ${label}`;
    }

    function buildMarketRequestUrl() {
        if (!marketElements.grid) {
            return "";
        }

        const baseUrl = marketElements.grid.dataset.ajaxUrl;

        if (!baseUrl) {
            return "";
        }

        const params = new URLSearchParams();

        if (marketState.search) {
            params.set("search", marketState.search);
        }

        if (marketState.recommendation) {
            params.set(
                "recommendation",
                marketState.recommendation
            );
        }

        if (marketState.risk) {
            params.set("risk", marketState.risk);
        }

        const queryString = params.toString();

        return queryString
            ? `${baseUrl}?${queryString}`
            : baseUrl;
    }

    async function fetchMarketAssets() {
        const requestUrl = buildMarketRequestUrl();

        if (!requestUrl || !marketElements.grid) {
            return;
        }

        if (marketState.controller) {
            marketState.controller.abort();
        }

        marketState.controller = new AbortController();
        marketState.lastRequestUrl = requestUrl;

        hideMarketError();
        setMarketLoading(true);

        try {
            const response = await fetch(requestUrl, {
                method: "GET",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json"
                },
                credentials: "same-origin",
                cache: "no-store",
                signal: marketState.controller.signal
            });

            if (!response.ok) {
                throw new Error(
                    `La solicitud AJAX falló con estado ${response.status}.`
                );
            }

            const data = await response.json();

            if (!data.success || typeof data.html !== "string") {
                throw new Error(
                    "La respuesta recibida no tiene el formato esperado."
                );
            }

            marketElements.grid.innerHTML = data.html;

            updateResultCounter(
                Number.isInteger(data.count)
                    ? data.count
                    : 0
            );

            animateLoadedAssetCards();

            if (
                typeof ScrollTrigger !== "undefined" &&
                typeof ScrollTrigger.refresh === "function"
            ) {
                ScrollTrigger.refresh();
            }
        } catch (error) {
            if (error.name === "AbortError") {
                return;
            }

            console.error(
                "Error al buscar activos mediante AJAX:",
                error
            );

            showMarketError();
        } finally {
            setMarketLoading(false);
        }
    }

    function scheduleMarketRequest() {
        window.clearTimeout(marketState.debounceTimer);

        marketState.debounceTimer = window.setTimeout(
            fetchMarketAssets,
            350
        );
    }

    function updateActiveFilterButton(selectedButton) {
        marketElements.filterButtons.forEach(function (button) {
            const isSelected = button === selectedButton;

            button.classList.toggle("active", isSelected);
            button.setAttribute(
                "aria-pressed",
                isSelected ? "true" : "false"
            );
        });
    }

    function resetMarketFilters() {
        marketState.recommendation = "";
        marketState.risk = "";
    }

    function handleFilterClick(button) {
        const filterType = button.dataset.filterType;
        const filterValue = button.dataset.filterValue;

        updateActiveFilterButton(button);
        resetMarketFilters();

        if (
            filterType === "recommendation" &&
            filterValue !== "all"
        ) {
            marketState.recommendation = filterValue;
        }

        if (
            filterType === "risk" &&
            filterValue !== "all"
        ) {
            marketState.risk = filterValue;
        }

        fetchMarketAssets();
    }

    function setupMarketAjax() {
        if (!marketElements.grid) {
            return;
        }

        marketElements.filterButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                handleFilterClick(button);
            });
        });

        if (marketElements.searchInput) {
            marketElements.searchInput.addEventListener(
                "input",
                function (event) {
                    marketState.search = event.target.value
                        .trim()
                        .slice(0, 100);

                    scheduleMarketRequest();
                }
            );
        }

        if (marketElements.retryButton) {
            marketElements.retryButton.addEventListener(
                "click",
                function () {
                    hideMarketError();
                    fetchMarketAssets();
                }
            );
        }

        animateLoadedAssetCards();
    }

    function createPortfolioCharts() {
        if (typeof Chart === "undefined") {
            return;
        }

        const labels = getJsonData(
            "portfolioLabelsData"
        );
        const values = getJsonData(
            "portfolioValuesData"
        );
        const returns = getJsonData(
            "portfolioReturnsData"
        );
        const scores = getJsonData(
            "portfolioScoresData"
        );

        if (!labels.length) {
            return;
        }

        Chart.defaults.color = "#cbd5e1";
        Chart.defaults.borderColor =
            "rgba(148, 163, 184, 0.18)";
        Chart.defaults.font.family =
            "Inter, Arial, sans-serif";

        const distributionCanvas = document.getElementById(
            "portfolioDistributionChart"
        );
        const returnsCanvas = document.getElementById(
            "portfolioReturnsChart"
        );
        const scoresCanvas = document.getElementById(
            "portfolioScoresChart"
        );

        if (distributionCanvas) {
            new Chart(distributionCanvas, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [
                        {
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
                                "rgba(132, 204, 22, 0.85)",
                                "rgba(244, 114, 182, 0.85)"
                            ]
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "62%",
                    animation: {
                        duration: 900,
                        easing: "easeOutQuart"
                    },
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                padding: 16,
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const value = Number(
                                        context.raw || 0
                                    );

                                    return (
                                        `${context.label}: USD ` +
                                        value.toLocaleString(
                                            "es-AR",
                                            {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2
                                            }
                                        )
                                    );
                                }
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
                    datasets: [
                        {
                            label: "Rentabilidad %",
                            data: returns,
                            borderRadius: 10,
                            backgroundColor: returns.map(
                                function (value) {
                                    return value >= 0
                                        ? "rgba(34, 197, 94, 0.85)"
                                        : "rgba(239, 68, 68, 0.85)";
                                }
                            )
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 850,
                        easing: "easeOutQuart"
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return (
                                        `Rentabilidad: ` +
                                        `${Number(context.raw).toFixed(2)}%`
                                    );
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function (value) {
                                    return `${value}%`;
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
                    datasets: [
                        {
                            label: "Score QuantEdge",
                            data: scores,
                            tension: 0.35,
                            fill: true,
                            borderWidth: 3,
                            borderColor:
                                "rgba(56, 189, 248, 1)",
                            backgroundColor:
                                "rgba(56, 189, 248, 0.12)",
                            pointBackgroundColor:
                                "rgba(34, 197, 94, 1)",
                            pointBorderColor: "#020617",
                            pointBorderWidth: 2,
                            pointRadius: 5,
                            pointHoverRadius: 7
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 950,
                        easing: "easeOutQuart"
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return (
                                        `Score QuantEdge: ` +
                                        `${Number(context.raw).toFixed(1)}/100`
                                    );
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            min: 0,
                            max: 100,
                            ticks: {
                                stepSize: 20
                            }
                        }
                    }
                }
            });
        }
    }

    registerGsapPlugins();
    createIntroTimeline();
    createScrollAnimations();
    setupMarketAjax();
    createPortfolioCharts();
});