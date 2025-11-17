import { useState, useMemo } from 'react';
import type { Tract } from '../api';
import '../styles.css'
interface NavigationBarProps {
    brandName: string;
    imageSrcPath: string;
    navItems: string[];
    tracts?: Tract[];
    onSelectTract?: (tract: Tract) => void;
}

export function NavigationBar({ brandName, imageSrcPath, navItems = [], tracts = [], onSelectTract }: NavigationBarProps) {
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const [isOpen, setIsOpen] = useState(false);
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [showSearchResults, setShowSearchResults] = useState(false);
    const MODES = ['all','county', 'cluster', 'geoid'] as const;
    type SearchMode = typeof MODES[number];

    const [searchMode, setSearchMode] = useState<SearchMode>('county');

    const toggle = () => setIsOpen((s) => !s);
    const close = () => setIsOpen(false);
    const toggleDropdown = (e: React.MouseEvent) => {
        e.preventDefault();
        setDropdownOpen((d) => !d);
    };

    const normalize = (v: unknown) => {
        return (v ?? '').toString().toLowerCase().normalize('NFKC').replace(/\s+/g, ' ').
        replace(/\u00a0/g, ' ').trim();
    }

    const fieldsForMode = (t: Tract, mode: SearchMode) => {
        switch (mode) {
            case 'all':
                return normalize(t.county_name) + ' ' + normalize(t.geoid) + ' ' + normalize(t.cluster_label);
            case 'county': return normalize(t.county_name);
            case 'geoid': return normalize(t.geoid);
            case 'cluster': return normalize(t.cluster_label);
        }
    }
    const searchResults = useMemo(() => {
        const query = normalize(searchQuery);
        if (!query || !tracts.length) return [];

        const prefix = tracts.filter(t => fieldsForMode(t, searchMode).startsWith(query))

        let results = prefix;

        if (results.length < 10 && query.length >= 3) {
            const substring = tracts.filter(t => {
                const f = fieldsForMode(t, searchMode);
                return !f.startsWith(query) && f.includes(query);
            })
            results = [...results, ...substring];
        }
        // Remove duplicates and return up to 10 results
        const uniqueMatches = new Map<string, Tract>();
        for (const t of results) {
            if (!uniqueMatches.has(t.geoid))
                uniqueMatches.set(t.geoid, t);
            if (uniqueMatches.size >= 10)
                break;
        }

        return Array.from(uniqueMatches.values())
    }, [searchQuery, tracts, searchMode]);

    const handleSelectResult = (tract: Tract) => {
        onSelectTract?.(tract);
        setSearchQuery('');
        setShowSearchResults(false);
    };

    const getDirectionBadge = (geoid: string) => {
        // Simple heuristic: use last digit of GEOID to suggest direction
        const lastDigit = parseInt(geoid.slice(-2), 10);
        if (lastDigit < 25) return '↑ North';
        if (lastDigit < 50) return '→ East';
        if (lastDigit < 75) return '↓ South';
        return '← West';
    };

    return (
        <nav className="navbar navbar-expand-md navbar-dark bg-dark shadow">
            <div className="container-fluid">

                <a className="navbar-brand d-flex align-items-center" href="#">
                    <img src={imageSrcPath}
                        width="60"
                        height="60"
                        className="d-inline-block align-middle me-2" alt="logo" />
                    <span className="fw-bolder fs-4">{brandName}</span>
                </a>
                <button
                    className="navbar-toggler"
                    type="button"
                    onClick={toggle}
                    aria-controls="navbarSupportedContent"
                    aria-expanded={isOpen}
                    aria-label="Toggle navigation"
                >
                    <span className="navbar-toggler-icon" />
                </button>

                <div className={`collapse navbar-collapse d-md-flex ${isOpen ? 'show' : ''}`} id="navbarSupportedContent">
                    <ul className="navbar-nav me-auto mb-2 mb-md-0 d-flex align-items-center flex-column flex-md-row w-100">
                        {navItems.map((items, index) => (
                            <li key={items}
                                className="nav-item">
                                <a
                                    className={selectedIndex === index ? "nav-link active fw-bold" : "nav-link"}
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        setSelectedIndex(index);
                                        close();
                                    }}
                                >
                                    {items}
                                </a>
                            </li>
                        ))}

                        <li className={"nav-item dropdown"}>
                            <a
                                className="nav-link dropdown-toggle"
                                href="#"
                                id="navbarDropdown"
                                role="button"
                                onClick={toggleDropdown}
                                aria-haspopup="true"
                                aria-expanded={dropdownOpen}
                            >
                                Dropdown
                            </a>
                            <div className={"dropdown-menu" + (dropdownOpen ? ' show' : '')} aria-labelledby="navbarDropdown">
                                <a className="dropdown-item" href="#" onClick={(e) => e.preventDefault()}>Action</a>
                                <a className="dropdown-item" href="#" onClick={(e) => e.preventDefault()}>Another action</a>
                                <div className="dropdown-divider"></div>
                                <a className="dropdown-item" href="#" onClick={(e) => e.preventDefault()}>Something else here</a>
                            </div>
                        </li>
                    </ul>
                    <form className="d-flex position-relative" onSubmit={(e) => {
                        e.preventDefault()
                        if (searchResults.length) handleSelectResult(searchResults[0]);
                    }}>                    <input
                            className="form-control me-2"
                            type="search"
                            placeholder="Search tracts..."
                            aria-label="Search"
                            value={searchQuery}
                            onChange={(e) => {
                                setSearchQuery(e.target.value);
                                setShowSearchResults(true);
                            }}
                            onFocus={() => setShowSearchResults(true)}
                        />
                        <select
                            className="form-select me-2"
                            style={{ width: '130px' }}
                            value={searchMode}
                            onChange={(e) => setSearchMode(e.target.value as SearchMode)}
                            aria-label="Search Mode"
                        >
                            <option value="all">All Fields</option>
                            <option value="county">County</option>
                            <option value="cluster">Cluster</option>
                            <option value="geoid">GeoID</option>
                        </select>

                        <button className="btn btn-outline-success" type="submit">Search</button>

                        {showSearchResults && searchQuery.trim().length > 0 && (
                            <div className="position-absolute bg-dark text-light rounded mt-2" style={{ top: '100%', right: 0, minWidth: '350px', zIndex: 1000 }}>
                                <div className="p-2">
                                    {searchResults.length > 0 ? (
                                        searchResults.map((tract) => (
                                            <div
                                                key={tract.geoid}
                                                className="p-3 border-bottom cursor-pointer hover-highlight"
                                                onClick={() => handleSelectResult(tract)}
                                                style={{ cursor: 'pointer' }}
                                            >
                                                <div className="d-flex justify-content-between align-items-start">
                                                    <div>
                                                        <div className="fw-bold text-light">{tract.county_name}</div>
                                                        <div className="small text-muted">Cluster {tract.cluster_label} • GEOID: {tract.geoid}</div>
                                                    </div>
                                                    <span className="badge bg-info text-dark ms-2">{getDirectionBadge(tract.geoid)}</span>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="p-3 text-muted text-center">No results found</div>
                                    )}
                                </div>
                            </div>
                        )}
                    </form>
                </div>
            </div>

        </nav>
    );
}