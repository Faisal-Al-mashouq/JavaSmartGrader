#!/usr/bin/env node
import { Command } from "commander";

//#region src/main.d.ts
/**
 * Checks if the current module is the main entry point.
 * Handles npm global bin symlinks by resolving real paths.
 *
 * @param importMetaUrl - The import.meta.url of the module
 * @param processArgv1 - The process.argv[1] value (path to executed script)
 * @returns true if this module is being run directly
 */
declare function isMainModule(importMetaUrl: string, processArgv1: string | undefined): boolean;
/**
 * Adds verbose and env-file options to all commands recursively,
 * and automatically records telemetry for all command invocations.
 */
declare function addCommonOptionsRecursively(command: Command): void;
/**
 * Gracefully shuts down all resources with a hard timeout guarantee.
 * If cleanup operations hang, the process will force exit after the timeout.
 */
declare const shutdownGracefully: () => Promise<void>;
//#endregion
export { addCommonOptionsRecursively, isMainModule, shutdownGracefully };
//# sourceMappingURL=main.d.ts.map