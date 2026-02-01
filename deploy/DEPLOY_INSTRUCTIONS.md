# Moltbook Observatory - Deployment Instructions

## Files Ready for Deployment

- `website.zip` - Production build of the React website (862 KB)

## Deployment to home.pl

### Option 1: SFTP Upload (Recommended)

Provide Claude Code with:
1. **SFTP Host**: e.g., `ftp.home.pl` or your server address
2. **Username**: Your FTP login
3. **Password**: Your FTP password
4. **Target path**: e.g., `/public_html/observatory/` or desired location

Claude will:
1. Connect via SFTP
2. Upload all files from `website/dist/`
3. Verify the upload

### Option 2: Manual Upload via FileZilla

1. Download FileZilla: https://filezilla-project.org/
2. Connect to your home.pl server
3. Navigate to target directory (e.g., `/public_html/observatory/`)
4. Upload contents of `C:\moltbook-observatory\website\dist\`

### Option 3: home.pl Web Panel

1. Log in to home.pl panel
2. Go to File Manager
3. Navigate to public_html (or subdirectory)
4. Upload `website.zip`
5. Extract the zip file
6. Delete the zip file

## Domain Configuration

After choosing a domain (e.g., `cambrianarchive.com`):

1. Buy the domain at registrar (Namecheap, GoDaddy, etc.)
2. Point DNS to home.pl nameservers:
   - `dns1.home.pl`
   - `dns2.home.pl`
   - `dns3.home.pl`
3. In home.pl panel, add the domain to your hosting
4. Wait for DNS propagation (up to 48h, usually faster)

## Post-Deployment Checklist

- [ ] Website loads at the target URL
- [ ] All pages work (landing, discoveries, feedback)
- [ ] Data files load correctly (`/data/discoveries.json`, etc.)
- [ ] Reports are accessible (`/reports/2026-01-31/`)
- [ ] SSL certificate is active (https://)

## Updating Content

To publish new reports:
1. Run the pipeline: `python scripts/run_all.py`
2. Rebuild website: `cd website && npm run build`
3. Upload new `dist/` contents to server

Or set up automated deployment (future enhancement).
