document.addEventListener("DOMContentLoaded", () => {
    const chartCanvas = document.getElementById(
        "historicalPriceChart"
    );

    if (!chartCanvas) {
        return;
    }

    const labelsElement = document.getElementById(
        "historicalLabelsData"
    );

    const pricesElement = document.getElementById(
        "historicalPricesData"
    );

    const sma20Element = document.getElementById(
        "historicalSma20Data"
    );

    const sma50Element = document.getElementById(
        "historicalSma50Data"
    );

    if (
        !labelsElement ||
        !pricesElement ||
        !sma20Element ||
        !sma50Element
    ) {
        return;
    }

    const labels = JSON.parse(
        labelsElement.textContent
    );

    const prices = JSON.parse(
        pricesElement.textContent
    );

    const sma20 = JSON.parse(
        sma20Element.textContent
    );

    const sma50 = JSON.parse(
        sma50Element.textContent
    );

    if (!labels.length || !prices.length) {
        return;
    }

    const context = chartCanvas.getContext("2d");

    const gradient = context.createLinearGradient(
        0,
        0,
        0,
        320
    );

    gradient.addColorStop(
        0,
        "rgba(56, 189, 248, 0.30)"
    );

    gradient.addColorStop(
        1,
        "rgba(56, 189, 248, 0.01)"
    );

    new Chart(
        context,
        {
            type: "line",

            data: {
                labels,

                datasets: [
                    {
                        label: "Precio de cierre",
                        data: prices,

                        borderColor: "#38bdf8",
                        backgroundColor: gradient,

                        fill: true,
                        borderWidth: 2.5,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        tension: 0.25,
                    },

                    {
                        label: "SMA 20",
                        data: sma20,

                        borderColor: "#22c55e",
                        backgroundColor: "transparent",

                        fill: false,
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        tension: 0.2,
                    },

                    {
                        label: "SMA 50",
                        data: sma50,

                        borderColor: "#f59e0b",
                        backgroundColor: "transparent",

                        fill: false,
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        tension: 0.2,
                    },
                ],
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                interaction: {
                    intersect: false,
                    mode: "index",
                },

                plugins: {
                    legend: {
                        display: true,

                        labels: {
                            color: "#cbd5e1",
                            usePointStyle: true,
                            pointStyle: "circle",
                        },
                    },

                    tooltip: {
                        callbacks: {
                            label(context) {
                                if (context.raw === null) {
                                    return "";
                                }

                                return (
                                    ` ${context.dataset.label}: `
                                    + Number(
                                        context.raw
                                    ).toFixed(2)
                                );
                            },
                        },
                    },
                },

                scales: {
                    x: {
                        grid: {
                            display: false,
                        },

                        ticks: {
                            color: "#94a3b8",
                            maxTicksLimit: 8,
                        },
                    },

                    y: {
                        grid: {
                            color: (
                                "rgba(148, 163, 184, 0.08)"
                            ),
                        },

                        ticks: {
                            color: "#94a3b8",
                        },
                    },
                },
            },
        }
    );
});