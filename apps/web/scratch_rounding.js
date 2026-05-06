const testValues = [
    "1.005", "1.015", "1.025", "1.035", "1.045", "1.055", "1.065", "1.075", "1.085", "1.095",
    "100.005", "100.015", "33.333333", "33.335", "33.345"
];

console.log("Testing JS toFixed(2)");
console.log("Input           | toFixed(2)");
console.log("------------------------------");
testValues.forEach(val => {
    const num = Number(val);
    const fixed = num.toFixed(2);
    console.log(`${val.padEnd(15)} | ${fixed.padEnd(10)}`);
});

function financialRound(num) {
    return Number(Math.round(num + "e+2") + "e-2");
}

console.log("\nTesting financialRound (custom)");
console.log("Input           | Rounded");
console.log("------------------------------");
testValues.forEach(val => {
    const num = Number(val);
    const rounded = financialRound(num).toFixed(2);
    console.log(`${val.padEnd(15)} | ${rounded.padEnd(10)}`);
});
