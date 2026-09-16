import { safeNextPath } from "@/lib/navigation";

test.each([
  ["/dashboard", "/dashboard"],
  ["/accounts", "/accounts"],
  ["/accounts?page=2", "/accounts?page=2"],
  ["/reports#top", "/reports#top"],
])("allows internal next path %s", (value, expected) => {
  expect(safeNextPath(value)).toBe(expected);
});

test.each([
  ["https://evil.example"],
  ["http://evil.example"],
  ["//evil.example"],
  ["javascript:alert(1)"],
  ["\\evil.example"],
  [""],
  [null],
])("rejects unsafe next path %s", value => {
  expect(safeNextPath(value)).toBe("/dashboard");
});
