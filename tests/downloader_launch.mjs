// Run only in a disposable ALACarte image with --network none and no user mounts.
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { spawnAmdp, writeAmdpConfig } from '/app/lib/amdpRunner.mjs'

const staging = await fs.mkdtemp(path.join(os.tmpdir(), 'octocarte-downloader-check-'))
try {
  await writeAmdpConfig({
    settings: { storefront: 'us', downloadLyrics: false },
    mediaUserToken: '',
    stagingRoot: staging,
  })
  for (const [mode, args] of [
    ['album', ['https://music.apple.com/us/album/_/1']],
    ['song', ['--song', 'https://music.apple.com/us/album/_/1?i=2']],
  ]) {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 10000)
    try {
      const { waitExit } = spawnAmdp({ args, cwd: staging, signal: controller.signal })
      const result = await waitExit
      // The pinned downloader must load its config and reach catalog access.
      // Network is disabled, so token lookup is the expected stopping point.
      if (result.code !== 0 || !`${result.stdout}\n${result.stderr}`.includes('Failed to get token.')) {
        throw new Error(`Unexpected offline downloader result in ${mode} mode (exit ${result.code})`)
      }
      console.log(`PASS: ALACarte ${mode} downloader launches from job staging and reaches offline catalog lookup`)
    } finally { clearTimeout(timeout) }
  }
} finally { await fs.rm(staging, { recursive: true, force: true }) }
