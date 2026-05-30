-- Use folder name to build extension name and tag. Version is specified explicitly.
local ext = get_current_extension_info()

project_ext (ext)

-- Link only those files and folders into the extension target directory.
-- xrmanifests/ is referenced from config/extension.toml via
--   xr.manifests."senckenberg.messelpit" = "xrmanifests"
-- so it needs to be on disk alongside the staged extension.
repo_build.prebuild_link {
    { "senckenberg", ext.target_dir.."/senckenberg" },
    { "xrmanifests", ext.target_dir.."/xrmanifests" },
}
