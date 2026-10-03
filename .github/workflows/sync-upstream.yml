name: Sync with upstream Library Sync

# Checks komadorirobin/library-sync.koplugin for a new release. When there is
# one, rebuilds this repo's renamed copy from it and publishes a release with
# the same version tag, so Storefront and the plugin's own "Check for updates"
# both pick it up.

on:
  schedule:
    - cron: "23 */3 * * *" # every 3 hours
  workflow_dispatch:
    inputs:
      rebuild:
        description: "Rebuild and republish the current version even if it already exists here"
        type: boolean
        default: false

permissions:
  contents: write
  actions: write

concurrency:
  group: sync-upstream
  cancel-in-progress: false

env:
  UPSTREAM: komadorirobin/library-sync.koplugin
  # Shown in KOReader menus: "Library Sync (Nonfiction)".
  VARIANT_LABEL: Nonfiction
  # Used inside settings file names (library_sync_nf_settings.txt). Do not
  # change this after you have configured the plugin, or it will look for its
  # settings under the new name and start unconfigured.
  VARIANT_ID: nf

jobs:
  sync:
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ github.token }}
      REBUILD: ${{ inputs.rebuild }}
    steps:
      - uses: actions/checkout@v4

      - name: Look for a new upstream release
        id: check
        run: |
          tag=$(gh api "repos/$UPSTREAM/releases/latest" --jq .tag_name)
          if [ -z "$tag" ]; then
            echo "Could not read the latest upstream release" >&2
            exit 1
          fi
          echo "tag=$tag" >> "$GITHUB_OUTPUT"
          if gh release view "$tag" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
            if [ "$REBUILD" = "true" ]; then
              echo "build=true" >> "$GITHUB_OUTPUT"
              echo "replace=true" >> "$GITHUB_OUTPUT"
              echo "Rebuilding $tag on request." >> "$GITHUB_STEP_SUMMARY"
            else
              echo "build=false" >> "$GITHUB_OUTPUT"
              echo "Already up to date with upstream $tag." >> "$GITHUB_STEP_SUMMARY"
            fi
          else
            echo "build=true" >> "$GITHUB_OUTPUT"
            echo "New upstream release $tag." >> "$GITHUB_STEP_SUMMARY"
          fi

      - name: Build the renamed copy
        if: steps.check.outputs.build == 'true'
        env:
          TAG: ${{ steps.check.outputs.tag }}
        run: |
          export VARIANT_OWNER="$GITHUB_REPOSITORY_OWNER"
          export VARIANT_REPO="${GITHUB_REPOSITORY#*/}"
          git clone --quiet --depth 1 --branch "$TAG" "https://github.com/$UPSTREAM.git" "$RUNNER_TEMP/upstream"
          python3 .github/scripts/make_variant.py "$RUNNER_TEMP/upstream" "$RUNNER_TEMP/out/$VARIANT_REPO"

      - name: Check that every Lua file still compiles
        if: steps.check.outputs.build == 'true'
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y -qq luajit
          cd "$RUNNER_TEMP/out/${GITHUB_REPOSITORY#*/}"
          find . -name '*.lua' -print0 | while IFS= read -r -d '' f; do
            luajit -bl "$f" > /dev/null || { echo "Syntax error in $f" >&2; exit 1; }
          done

      - name: Commit, tag and publish
        if: steps.check.outputs.build == 'true'
        env:
          TAG: ${{ steps.check.outputs.tag }}
          REPLACE: ${{ steps.check.outputs.replace }}
        run: |
          repo="${GITHUB_REPOSITORY#*/}"
          out="$RUNNER_TEMP/out"

          # Keep the built plugin at the repo root (as upstream does), next to .github/.
          find . -mindepth 1 -maxdepth 1 ! -name .git ! -name .github -exec rm -rf {} +
          cp -a "$out/$repo/." ./
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A
          git commit -q -m "Library Sync $TAG (built from $UPSTREAM)" || echo "No file changes."
          git push -q origin HEAD

          if [ "$REPLACE" = "true" ]; then
            gh release delete "$TAG" --yes --cleanup-tag || true
            sleep 5
          fi

          (cd "$out" && zip -q -r "$repo.zip" "$repo")
          {
            echo "Automatically built from [$UPSTREAM $TAG](https://github.com/$UPSTREAM/releases/tag/$TAG)."
            echo
            gh api "repos/$UPSTREAM/releases/tags/$TAG" --jq '.body // ""'
          } > "$RUNNER_TEMP/notes.md"
          gh release create "$TAG" "$out/$repo.zip" \
            --target "$(git rev-parse HEAD)" \
            --title "Library Sync ($VARIANT_LABEL) $TAG" \
            --notes-file "$RUNNER_TEMP/notes.md"
          echo "Published $TAG." >> "$GITHUB_STEP_SUMMARY"

      # GitHub pauses scheduled workflows in repos with no activity for 60
      # days. Re-enabling the workflow through the API resets that timer.
      - name: Keep the schedule alive
        if: always()
        continue-on-error: true
        run: gh workflow enable sync-upstream.yml --repo "$GITHUB_REPOSITORY"
