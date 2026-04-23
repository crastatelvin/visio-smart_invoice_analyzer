import { render, screen } from "@testing-library/react";
import App from "./App";

test("renders VISIO heading", () => {
  render(<App />);
  expect(screen.getByText("VISIO")).toBeInTheDocument();
});
