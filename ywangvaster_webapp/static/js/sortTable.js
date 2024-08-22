function sortTable(tableBodyId, columnN, compareType = "") {
  const tableBody = document.getElementById(tableBodyId);
  const rows = Array.from(tableBody.rows); // Exclude the header row
  const currentDirection = tableBody.getAttribute("data-sort-direction") || "asc";
  const newDirection = currentDirection === "asc" ? "desc" : "asc";

  rows.sort((a, b) => {
    const aValue = a.getElementsByTagName("td")[columnN].textContent.trim();
    const bValue = b.getElementsByTagName("td")[columnN].textContent.trim();

    let result = compareOnColumnType(aValue, bValue, compareType);

    return newDirection === "asc" ? result : -result;
  });

  tableBody.setAttribute("data-sort-direction", newDirection);

  // Remove existing arrows
  document.querySelectorAll(".sort-arrow").forEach((arrow) => {
    arrow.classList.remove("sort-asc", "sort-desc");
  });

  // Add new arrow
  const arrow = document.getElementById(`arrow-${columnN}`);
  arrow.classList.add(newDirection === "asc" ? "sort-asc" : "sort-desc");

  rows.forEach((row) => tableBody.appendChild(row));
}

function compareOnColumnType(value1, value2, compareType = "") {
  if (value1 === value2) return 0;

  // Convert to lower case strings for easier comparison
  const val1Lower = value1.toString().toLowerCase();
  const val2Lower = value2.toString().toLowerCase();

  // Force different comparison types if given.
  if (compareType === "string") {
    return val1Lower.localeCompare(val2Lower);
  } else if (compareType === "date") {
    // Parse as dates (ISO datetime format)
    const date1 = new Date(value1);
    const date2 = new Date(value2);
    return date1 - date2;
  }

  // Check if values can be parsed as booleans
  const boolValues = { true: true, false: false };
  const isBool1 = val1Lower in boolValues;
  const isBool2 = val2Lower in boolValues;

  if (isBool1 && isBool2) {
    return boolValues[val1Lower] - boolValues[val2Lower];
  }

  // Check if values can be parsed as numbers
  const num1 = parseFloat(value1);
  const num2 = parseFloat(value2);
  const isNum1 = typeof num1 === "number" && !isNaN(num1);
  const isNum2 = typeof num2 === "number" && !isNaN(num2);

  if (isNum1 && isNum2) {
    return num1 - num2;
  }

  // Convert to dates
  const date1 = new Date(val1Lower);
  const date2 = new Date(val2Lower);
  const isValidDate1 = !isNaN(date1.getDate());
  const isValidDate2 = !isNaN(date2.getDate());

  if (isValidDate1 && isValidDate2) {
    return date1 - date2;
  }

  // Default to string comparison
  return val1Lower.localeCompare(val2Lower);
}
