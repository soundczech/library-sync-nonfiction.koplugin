# Installing Library Sync

## 1. Copy the plugin

Copy the complete `library-sync.koplugin` directory to KOReader's plugin directory:

```text
<koreader>/plugins/library-sync.koplugin/
```

The files must be directly inside that directory, not inside a second nested directory. At minimum, verify that these paths exist:

```text
<koreader>/plugins/library-sync.koplugin/_meta.lua
<koreader>/plugins/library-sync.koplugin/main.lua
<koreader>/plugins/library-sync.koplugin/providers/init.lua
```

`<koreader>` is KOReader's user storage directory on the device.

Existing installations may still use `<koreader>/plugins/grimmory-sync.koplugin/`. That legacy directory name is supported for OTA updates. Do not keep both `library-sync.koplugin` and `grimmory-sync.koplugin` installed at the same time.

## 2. Restart KOReader

Exit KOReader completely and start it again. Backgrounding the Android application is not sufficient; force-stop it if necessary.

## 3. Configure the plugin

Open:

```text
Menu -> Magnifying glass -> Library Sync -> Configure
```

Choose Grimmory or BookOrbit, enter the server origin URL or full `/api/v1/opds` URL and the OPDS credentials, then choose a writable local book directory.

For Grimmory, use the KOReader Sync credentials for OPDS. The optional normal Grimmory account credentials enable extra series metadata, genres, tags, Hardcover identifiers, original filenames, and Bookshelf author images.

For BookOrbit, create dedicated OPDS credentials under BookOrbit's OPDS settings. The optional normal BookOrbit account credentials enable extra genres, tags, Hardcover identifiers, and Bookshelf author images.

## 4. Run the first sync

Open:

```text
Menu -> Magnifying glass -> Library Sync -> Sync missing books
```

Start with a restricted shelf, collection, or SmartScope if you want to verify the resulting folder and filename layout before syncing the full library.

By default, sync only downloads missing books and never removes local files. Enable `Mirror selected sync source` only if you want Library Sync to move manifest-tracked books removed from the selected source, and older manifest-tracked duplicates of the same server book, to `<library>/.library-sync-trash/`.

Mirror requires a complete paginated OPDS response with a verifiable total. Unsupported entries count as present for Mirror safety but are not downloaded. EPUB and CBZ files are managed by Mirror. Mirror also asks for an additional confirmation before a large cleanup. If books need to be recovered, open `Library Sync -> Restore books from Mirror trash`. Restored files return to their original relative paths; existing destination files are skipped and never overwritten.

## Troubleshooting

| Problem | Check |
| --- | --- |
| Plugin is missing | Confirm the `.koplugin` directory name, file nesting, and restart KOReader. |
| Connection fails | Confirm the device can reach the server origin over the network. |
| OPDS returns 401 | Use OPDS credentials, not normal server account credentials. |
| Extra metadata is absent | Configure the optional normal server account credentials. |
| Metadata refresh unexpectedly selects most books | Cancel it. Update Library Sync, verify API credentials, then retry; large queues require a second confirmation. |
| Extra metadata fails behind a proxy or tunnel | Use the public `https://` server URL. |
| No books are downloaded | Confirm the selected sync source contains EPUB or CBZ files and the local path is writable. |
| Author images fail | Enable Bookshelf integration and verify API credentials. |
| Author image upload fails | Use BookOrbit account credentials with permission to edit metadata. Existing server images and ambiguous matches are skipped. |
| Books were moved by Mirror | Disable Mirror, then use `Restore books from Mirror trash`. Existing files are not overwritten. |

KOReader's log is normally located at:

```text
<koreader>/crash.log
```

Search for `[GrimmorySync]`, `grimmorysync`, or `library_sync`; some internal identifiers retain the old Grimmory name for compatibility.
