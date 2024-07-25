// This dynamically creates the table of the task for the start and end times of the selected schedule/s
function makeTaskTable(divToUpdate) {
  // Clear div area of existing elements
  clearDivElement(divToUpdate);

  // Grab data from DJango
  let tasksData = JSON.parse(document.getElementById("tasks_data").textContent);

  let seriesKeys = Object.keys(tasksData);
  let numSeries = seriesKeys.length;

  // Function to create a table from data

  let table = document.createElement("table");
  table.classList.add("table");
  table.classList.add("table-hover");
  table.id = "taskTable";
  let thead = table.createTHead();
  let tbody = table.createTBody();
  tbody.id = "taskTableBody";

  // Initial group header for spacing reasons
  let groupHeaderRow = thead.insertRow();
  let thInitial = document.createElement("th");
  thInitial.setAttribute("colspan", "2");
  groupHeaderRow.appendChild(thInitial);

  // Add table initial headers
  let headerRow = thead.insertRow();
  let thID = document.createElement("th");
  thID.setAttribute("onclick", "sortTable(0)");
  thID.textContent = "ID";
  headerRow.appendChild(thID);

  let thName = document.createElement("th");
  thName.textContent = "Task name";
  thName.setAttribute("onclick", "sortTable(1)");
  headerRow.appendChild(thName);

  for (let iSeries = 0; iSeries < numSeries; iSeries++) {
    let key = seriesKeys[iSeries];

    let thGroup = document.createElement("th");
    thGroup.setAttribute("colspan", "2");
    thGroup.textContent = key;
    thGroup.style = `background: ${thGroupStyiling[iSeries]}; border-radius: 8px;`;
    groupHeaderRow.appendChild(thGroup);

    let thStart = document.createElement("th");
    thStart.textContent = "Start";
    thStart.setAttribute("onclick", `sortTable(${2 + iSeries * 2})`);

    headerRow.appendChild(thStart);
    let thEnd = document.createElement("th");
    thEnd.textContent = "End";
    thEnd.setAttribute("onclick", `sortTable(${3 + iSeries * 2})`);
    headerRow.appendChild(thEnd);

    // Loop through each task
    for (let i = 0; i < tasksData[key].length; i++) {
      let rowId = `task_${tasksData[key][i][0]}`;

      // if tr of id doesnt already exist, add the start and end time
      let oldRow = false;
      for (let findRow of table.rows) {
        if (findRow.id === rowId) {
          oldRow = findRow;
          break;
        }
      }

      if (oldRow) {
        // add in empty cells
        if (oldRow.cells.length < 2 * (iSeries + 1)) {
          for (let k = 0; k < 2 * (iSeries + 1); k++) {
            let cell = oldRow.insertCell();
            cell.textContent = "";
          }
        }

        // add the start
        let cellStart = oldRow.insertCell();
        cellStart.textContent = tasksData[key][i][1];

        // add the end
        let cellEnd = oldRow.insertCell();
        cellEnd.textContent = tasksData[key][i][2];
      } else {
        // add new row
        let row = tbody.insertRow();
        row.id = rowId.trim();

        // Add the ID and name
        for (let j of [3, 0]) {
          let cell = row.insertCell();
          cell.textContent = tasksData[key][i][j];
        }

        // add in empty cells
        for (let k = 0; k < 2 * iSeries; k++) {
          let cell = row.insertCell();
          cell.textContent = "";
        }

        // add in the start and end times
        for (let j of [1, 2]) {
          let cell = row.insertCell();
          cell.textContent = tasksData[key][i][j];
        }
      }
    }
  }

  // Find the container div to update the table
  let dataTableContainer = document.getElementById(divToUpdate);
  dataTableContainer.appendChild(table);
}

function sortTable(n) {
  const tableBody = document.getElementById("taskTableBody");
  const rows = Array.from(tableBody.rows); // Exclude the header row

  const direction = tableBody.getAttribute("data-sort-direction") === "asc" ? 1 : -1;

  rows.sort((a, b) => {
    const aValue = a.getElementsByTagName("td")[n].textContent.trim();
    const bValue = b.getElementsByTagName("td")[n].textContent.trim();

    let result = compareOnColumnType(n, aValue, bValue);

    // If the values are equal, compare additional columns for stability
    if (result === 0) {
      for (let i = 0; i < a.cells.length; i++) {
        if (i !== n) {
          const aAdditional = a.getElementsByTagName("td")[i].textContent.trim();
          const bAdditional = b.getElementsByTagName("td")[i].textContent.trim();
          result = compareOnColumnType(i, aAdditional, bAdditional);
          if (result !== 0) {
            break;
          }
        }
      }
    }

    return direction * result;
  });

  // Update the sort direction
  tableBody.setAttribute("data-sort-direction", direction === 1 ? "desc" : "asc");

  // Re-append sorted rows to the table
  rows.forEach((row) => tableBody.appendChild(row));
}

function compareOnColumnType(columnId, value1, value2) {
  // compare incoming strings, based on the column of origin.
  if (columnId === 0) {
    return parseInt(value1) - parseInt(value2);
  } else if (columnId === 1) {
    return value1.toLowerCase().localeCompare(value2.toLowerCase());
  } else {
    const date1 = new Date(value1);
    const date2 = new Date(value2);
    return date1 - date2;
  }
}
