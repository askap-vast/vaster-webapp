// function sortTable(tableBodyId, columnN, compareType) {
//   const tableBody = document.getElementById(tableBodyId);
//   const rows = Array.from(tableBody.rows); // Exclude the header row

//   const direction = tableBody.getAttribute("data-sort-direction") === "asc" ? 1 : -1;

//   rows.sort((a, b) => {
//     const aValue = a.getElementsByTagName("td")[columnN].textContent.trim();
//     const bValue = b.getElementsByTagName("td")[columnN].textContent.trim();

//     let result = compareOnColumnType(compareType, aValue, bValue);

//     // If the values are equal, compare additional columns for stability
//     if (result === 0) {
//       for (let i = 0; i < a.cells.length; i++) {
//         if (i !== columnN) {
//           const aAdditional = a.getElementsByTagName("td")[i].textContent.trim();
//           const bAdditional = b.getElementsByTagName("td")[i].textContent.trim();
//           result = compareOnColumnType(i, aAdditional, bAdditional);
//           console.log("Compare result:", result);
//           if (result !== 0) {
//             break;
//           }
//         }
//       }
//     }

//     return direction * result;
//   });

//   // Update the sort direction
//   tableBody.setAttribute("data-sort-direction", direction === 1 ? "desc" : "asc");

//   // Re-append sorted rows to the table
//   rows.forEach((row) => tableBody.appendChild(row));
// }

// function compareOnColumnType(compareType, value1, value2) {
//   // Return the difference between two values in the table for sorting

//   if (value1 === value2) {
//     // Do nothing as they are the same value
//     return 0;
//   }

//   if (compareType === "number") {
//     // Parse the column as a number (integer or float)
//     return parseFloat(value1) - parseFloat(value2);
//   } else if (compareType === "date") {
//     // Parse as dates (ISO datetime format)
//     const date1 = new Date(value1);
//     const date2 = new Date(value2);
//     return date1 - date2;
//   } else if (compareType === "string") {
//     // Parse the cells as strings
//     return value1.toLowerCase().localeCompare(value2.toLowerCase());
//   } else {
//     // Default method
//     return value1.toLowerCase().localeCompare(value2.toLowerCase());
//   }
// }

// With table sorting added

function sortTable(tableBodyId, columnN, compareType) {
  const tableBody = document.getElementById(tableBodyId);
  const rows = Array.from(tableBody.rows); // Exclude the header row
  const currentDirection = tableBody.getAttribute("data-sort-direction") || "asc";
  const newDirection = currentDirection === "asc" ? "desc" : "asc";

  rows.sort((a, b) => {
    const aValue = a.getElementsByTagName("td")[columnN].textContent.trim();
    const bValue = b.getElementsByTagName("td")[columnN].textContent.trim();

    let result = compareOnColumnType(compareType, aValue, bValue);

    if (result === 0) {
      for (let i = 0; i < a.cells.length; i++) {
        if (i !== columnN) {
          const aAdditional = a.getElementsByTagName("td")[i].textContent.trim();
          const bAdditional = b.getElementsByTagName("td")[i].textContent.trim();
          result = compareOnColumnType(i, aAdditional, bAdditional);
          if (result !== 0) {
            break;
          }
        }
      }
    }

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

function compareOnColumnType(compareType, value1, value2) {
  if (value1 === value2) return 0;

  if (compareType === "number") {
    return parseFloat(value1) - parseFloat(value2);
  } else if (compareType === "date") {
    const date1 = new Date(value1);
    const date2 = new Date(value2);
    return date1 - date2;
  } else if (compareType === "string") {
    return value1.toLowerCase().localeCompare(value2.toLowerCase());
  } else {
    return value1.toLowerCase().localeCompare(value2.toLowerCase());
  }
}
