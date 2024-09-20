class MultiInputSlider extends HTMLElement {
  constructor() {
    super();
    this.container = document.createElement("div");
    this.container.setAttribute("id", "multi-input-slider-container");
    this.container.classList.add("multi-input-wrapper");

    const style = document.createElement("style");
    style.textContent = `
        .multi-input-wrapper {
            display: inline-block;
            padding: 15px;
            margin: 10px;
            width: 275px;
            border: 1px solid black;
            border-radius: 10px;
            background-color: #f0f0f0;
            align-items: center;
            flex-direction: row;
        }
        .multi-input-container {
            display: flex;
            align-items: center;
            flex-direction: row;
            padding: 5px;
        }
        .multi-input-container-slider {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .multi-input-container-label {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .multi-input-container label {
            padding: 4px;
        }
        .multi-input-container input {
            margin: 5px 0;
            width: 55%;
        }
      `;
    this.styleElement = style;
  }

  connectedCallback() {
    this.appendChild(this.styleElement);
    this.appendChild(this.container);
    this.render();
  }

  static get observedAttributes() {
    return ["num-sliders", "slider-min", "slider-max", "initial-values"];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (["num-sliders", "slider-min", "slider-max", "initial-values"].includes(name) && oldValue !== newValue) {
      this.render();
    }
  }

  createSlider(
    parent,
    sliderLabel = "",
    numSliders = 2,
    minSliderValue = 0.0,
    maxSliderValue = 1.0,
    initialValues = null
  ) {
    const labelDiv = this.createElement("div");
    labelDiv.classList.add("multi-input-container-label");
    const inputLabel = this.createElement("h6");
    inputLabel.innerText = sliderLabel;
    labelDiv.appendChild(inputLabel);
    parent.append(labelDiv);

    let minMaxDiff = parseFloat(maxSliderValue) - parseFloat(minSliderValue);

    // Initialize the array of values if not given.
    let values = [];
    if (initialValues) {
      initialValues = JSON.parse(initialValues);
      if (parseInt(numSliders) !== 1) {
        if (initialValues.length === parseInt(numSliders)) {
          values = initialValues.map((v, i) =>
            v ? (parseFloat(v) - parseFloat(minSliderValue)) / minMaxDiff : i / (numSliders - 1)
          );
        } else {
          values = Array.from({ length: numSliders }, (_, i) => i / (numSliders - 1));
        }
      } else {
        values = [0.5];
      }
    } else {
      values = Array.from({ length: numSliders }, (_, i) => i / (numSliders - 1));
    }

    const state = {
      start: 0,
      current: 0,
      active: 0,
    };

    const outer = this.createElement("div", {
      position: "relative",
      align: "center",
      left: "25px",
      width: "200px",
      height: "8px",
      backgroundColor: "gray",
      borderRadius: "5px",
    });
    parent.appendChild(outer);

    const shim = this.createElement("div", {
      position: "fixed",
      top: "0px",
      left: "0px",
      width: "100%",
      height: "100%",
      overflow: "hidden",
      zIndex: "9999",
      display: "none",
    });
    shim.addEventListener("mousemove", (event) => {
      state.current = event.screenX;
      render();
    });
    shim.addEventListener("mouseup", (event) => {
      state.current = event.screenX;
      render();
      shim.style.display = "none";
      inners[state.active].style.zIndex = "";
    });

    const sliderDiv = this.createElement("div");
    sliderDiv.classList.add("multi-input-container-slider");
    sliderDiv.appendChild(shim);
    parent.appendChild(sliderDiv);

    const inners = values.map((v, i) => {
      const inner = this.createElement("div", {
        position: "absolute",
        top: "-4px",
        left: `calc(${v * 98}% - 8px)`,
        width: "15px",
        height: "15px",
        border: "solid black 1px",
        borderRadius: "10px",
        backgroundColor: "lightgray",
      });
      inner.addEventListener("mousedown", (event) => {
        state.active = i;
        state.current = event.screenX;
        state.start = event.screenX;
        shim.style.display = "flex";
        inner.style.zIndex = "2";
      });
      outer.appendChild(inner);
      return inner;
    });

    const inputContainer = this.createElement("div", {
      marginTop: "5px",
    });

    const elementId = this.getAttribute("id");
    inputContainer.classList.add("multi-input-container");
    inputContainer.setAttribute("id", `${elementId}-input-container`);

    values[0] = Number.isNaN(values[0]) ? 0.0 : values[0];

    values.forEach((value, index) => {
      let inputDiv = this.createElement("div");
      inputDiv.classList.add("fieldWrapper");

      const input = this.createElement("input");
      input.value = value;
      input.name = index === 0 ? `${elementId}__gte` : `${elementId}__lte`;

      if (elementId) {
        if (parseInt(numSliders) === 2) {
          input.id = index === 0 ? `id_${elementId}__gte` : `id_${elementId}__lte`;
        } else {
          input.id = `${elementId}-slider-${index}`;
        }
      }

      // text for label for the Input element.
      const label = this.createElement("label");
      if (numSliders == 2) {
        label.innerHTML = index == 0 ? "Min:" : "Max: ";
      } else {
        label.innerHTML = `${index}: `;
      }
      label.setAttribute("for", input.id);

      input.addEventListener("input", (event) => {
        values[index] = parseFloat((event.target.value - minSliderValue) / minMaxDiff);
        this.value = values[index];
        render(true, index);
      });

      inputDiv.appendChild(label);
      inputDiv.appendChild(input);
      inputContainer.appendChild(inputDiv);
    });
    parent.appendChild(inputContainer);

    const render = (skipInputs = false, incomingIndex = null) => {
      values = values.map((v) => (Number.isNaN(v) ? 0.0 : v));

      let index = state.active;

      if (incomingIndex === 0) {
        index = 0;
      } else if (incomingIndex === 1) {
        index = 1;
      }

      const prev = index === 0 ? 0.0 : values[index - 1];
      const next = index === values.length - 1 ? 1.0 : values[index + 1];

      const delta = (state.current - state.start) / outer.offsetWidth;
      let value = values[index] + delta;
      if (value < prev) value = prev;
      if (value > next) value = next;
      values[index] = value;
      state.start = state.current;
      inners[index].style.left = `calc(${98 * value}% - 8px)`;

      if (!skipInputs) {
        const inputs = inputContainer.querySelectorAll("input");
        values.forEach((value, i) => {
          value = Number.isNaN(value) ? 0.0 : value;
          inputs[i].value = (minMaxDiff * value + parseFloat(minSliderValue)).toFixed(2);
        });
      }
    };

    render();
  }

  createElement(type = "div", styles = {}) {
    const el = document.createElement(type);
    Object.assign(el.style, styles);
    return el;
  }

  render() {
    const container = this.querySelector("#multi-input-slider-container");

    const sliderLabel = this.getAttribute("label");

    const numSliders = this.getAttribute("num-sliders") || 2;
    const minSliderValue = this.getAttribute("slider-min") || 0.0;
    const maxSliderValue = this.getAttribute("slider-max") || 1.0;

    // Initial values are in the scale of the min and max values
    const initialValues = this.getAttribute("initial-values") || null;

    if (container) {
      container.innerHTML = ""; // Clear previous content
      this.createSlider(container, sliderLabel, numSliders, minSliderValue, maxSliderValue, initialValues);
    }
  }
}

customElements.define("multi-input-slider", MultiInputSlider);
