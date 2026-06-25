import packageLock from "../package-lock.json";
import { describe, expect, it } from "vitest";

type PackageLock = {
  packages: Record<string, { version?: string }>;
};

const lock = packageLock as PackageLock;

function parseSemver(version: string): [number, number, number] {
  const [major, minor, patch] = version.split(".").map((part) => Number(part));
  return [major, minor, patch];
}

function isAtLeast(version: string, minimum: string): boolean {
  const [major, minor, patch] = parseSemver(version);
  const [minMajor, minMinor, minPatch] = parseSemver(minimum);
  if (major !== minMajor) return major > minMajor;
  if (minor !== minMinor) return minor > minMinor;
  return patch >= minPatch;
}

describe("package-lock security floors", () => {
  it("pins js-yaml to 4.2.0 or later", () => {
    const versions = Object.entries(lock.packages)
      .filter(([name]) => name.endsWith("/js-yaml") || name === "node_modules/js-yaml")
      .map(([, pkg]) => pkg.version)
      .filter((version): version is string => Boolean(version));

    expect(versions.length).toBeGreaterThan(0);
    for (const version of versions) {
      expect(isAtLeast(version, "4.2.0"), `js-yaml ${version} is below 4.2.0`).toBe(true);
    }
  });
});
