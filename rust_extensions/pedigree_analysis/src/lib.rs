use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap, HashSet};

fn norm(value: &str) -> String {
    value.trim().to_string()
}

fn is_missing(value: &str) -> bool {
    let text = value.trim();
    if text.is_empty() {
        return true;
    }
    matches!(
        text.to_ascii_lowercase().as_str(),
        "0" | "na" | "n/a" | "none" | "null"
    )
}

fn normalize_parent(value: &str) -> String {
    if is_missing(value) {
        "0".to_string()
    } else {
        norm(value)
    }
}

fn sex_code(value: &str) -> Option<char> {
    let text = value.trim().to_ascii_lowercase();
    if text.is_empty() || matches!(text.as_str(), "0" | "na" | "n/a" | "none" | "null") {
        None
    } else if matches!(
        text.as_str(),
        "m" | "male" | "1" | "sire" | "father" | "公" | "雄" | "父"
    ) {
        Some('M')
    } else if matches!(
        text.as_str(),
        "f" | "female" | "2" | "dam" | "mother" | "母" | "雌"
    ) {
        Some('F')
    } else {
        None
    }
}

fn parse_birthdate(value: &str) -> Option<i64> {
    let text = value.trim();
    if text.is_empty()
        || matches!(
            text.to_ascii_lowercase().as_str(),
            "0" | "na" | "n/a" | "none" | "null"
        )
    {
        return None;
    }
    let digits: String = text.chars().filter(|ch| ch.is_ascii_digit()).collect();
    if digits.len() >= 8 {
        digits[..8].parse::<i64>().ok()
    } else {
        text.parse::<f64>()
            .ok()
            .map(|value| (value * 1000.0) as i64)
    }
}

fn py_string_list(py: Python<'_>, values: &[String]) -> PyResult<Py<PyAny>> {
    Ok(PyList::new(py, values)?.into_any().unbind())
}

fn stats(values: &[f64]) -> (usize, f64, f64, f64, f64) {
    if values.is_empty() {
        return (0, f64::NAN, f64::NAN, f64::NAN, f64::NAN);
    }
    let total = values.len();
    let min = values
        .iter()
        .fold(f64::INFINITY, |acc, value| acc.min(*value));
    let max = values
        .iter()
        .fold(f64::NEG_INFINITY, |acc, value| acc.max(*value));
    let mean = values.iter().sum::<f64>() / total as f64;
    let sd = if total > 1 {
        let variance = values
            .iter()
            .map(|value| (value - mean).powi(2))
            .sum::<f64>()
            / (total - 1) as f64;
        variance.sqrt()
    } else {
        0.0
    };
    (total, min, max, mean, sd)
}

fn set_stats(py: Python<'_>, values: &[f64]) -> PyResult<PyObject> {
    let (total, min, max, mean, sd) = stats(values);
    let dict = PyDict::new(py);
    dict.set_item("total", total)?;
    dict.set_item("min", min)?;
    dict.set_item("max", max)?;
    dict.set_item("mean", mean)?;
    dict.set_item("sd", sd)?;
    Ok(dict.into_any().unbind())
}

fn detect_loops(
    ids: &[String],
    sires: &[String],
    dams: &[String],
    id_set: &HashSet<String>,
) -> Vec<Vec<String>> {
    let mut parent_map: HashMap<String, Vec<String>> = HashMap::new();
    for i in 0..ids.len() {
        let mut parents = Vec::new();
        if sires[i] != "0" && id_set.contains(&sires[i]) {
            parents.push(sires[i].clone());
        }
        if dams[i] != "0" && id_set.contains(&dams[i]) {
            parents.push(dams[i].clone());
        }
        parent_map.insert(ids[i].clone(), parents);
    }

    fn dfs(
        node: &str,
        parent_map: &HashMap<String, Vec<String>>,
        visited: &mut HashSet<String>,
        stack: &mut HashSet<String>,
        path: &mut Vec<String>,
        cycles: &mut Vec<Vec<String>>,
    ) {
        if stack.contains(node) {
            let mut cycle = Vec::new();
            let mut in_cycle = false;
            for item in path.iter() {
                if item == node {
                    in_cycle = true;
                }
                if in_cycle {
                    cycle.push(item.clone());
                }
            }
            cycle.push(node.to_string());
            cycles.push(cycle);
            return;
        }
        if visited.contains(node) {
            return;
        }
        visited.insert(node.to_string());
        stack.insert(node.to_string());
        path.push(node.to_string());
        if let Some(parents) = parent_map.get(node) {
            for parent in parents {
                dfs(parent, parent_map, visited, stack, path, cycles);
            }
        }
        path.pop();
        stack.remove(node);
    }

    let mut visited = HashSet::new();
    let mut stack = HashSet::new();
    let mut cycles = Vec::new();
    for id in ids {
        let mut path = Vec::new();
        dfs(
            id,
            &parent_map,
            &mut visited,
            &mut stack,
            &mut path,
            &mut cycles,
        );
    }
    cycles
}

fn longest_ancestral_path(
    ids: &[String],
    sires: &[String],
    dams: &[String],
    id_set: &HashSet<String>,
) -> Vec<usize> {
    fn depth_for(
        index: usize,
        id_to_index: &HashMap<String, usize>,
        sires: &[String],
        dams: &[String],
        id_set: &HashSet<String>,
        memo: &mut Vec<Option<usize>>,
        visiting: &mut HashSet<usize>,
    ) -> usize {
        if let Some(value) = memo[index] {
            return value;
        }
        if !visiting.insert(index) {
            memo[index] = Some(0);
            return 0;
        }
        let mut depth = 0usize;
        for parent in [&sires[index], &dams[index]] {
            if parent == "0" || !id_set.contains(parent) {
                continue;
            }
            if let Some(parent_index) = id_to_index.get(parent) {
                depth = depth.max(
                    depth_for(
                        *parent_index,
                        id_to_index,
                        sires,
                        dams,
                        id_set,
                        memo,
                        visiting,
                    ) + 1,
                );
            }
        }
        visiting.remove(&index);
        memo[index] = Some(depth);
        depth
    }

    let id_to_index: HashMap<String, usize> = ids
        .iter()
        .enumerate()
        .map(|(index, id)| (id.clone(), index))
        .collect();
    let mut memo = vec![None; ids.len()];
    let mut depths = Vec::with_capacity(ids.len());
    for index in 0..ids.len() {
        let mut visiting = HashSet::new();
        depths.push(depth_for(
            index,
            &id_to_index,
            sires,
            dams,
            id_set,
            &mut memo,
            &mut visiting,
        ));
    }
    depths
}

fn inbreeding(ids: &[String], sires: &[String], dams: &[String]) -> Result<Vec<f64>, String> {
    let n = ids.len();
    let mut id_to_index: HashMap<String, usize> = HashMap::with_capacity(n * 2);
    for (index, id) in ids.iter().enumerate() {
        if id_to_index.insert(id.clone(), index).is_some() {
            return Err(format!("Duplicate ID found in pedigree: {}", id));
        }
    }

    let mut sire_idx = vec![None; n];
    let mut dam_idx = vec![None; n];
    let mut children = vec![Vec::<usize>::new(); n];
    let mut indegree = vec![0usize; n];
    for i in 0..n {
        if sires[i] != "0" {
            if let Some(parent) = id_to_index.get(&sires[i]) {
                sire_idx[i] = Some(*parent);
                children[*parent].push(i);
                indegree[i] += 1;
            }
        }
        if dams[i] != "0" {
            if let Some(parent) = id_to_index.get(&dams[i]) {
                dam_idx[i] = Some(*parent);
                children[*parent].push(i);
                indegree[i] += 1;
            }
        }
    }

    let mut ready: BinaryHeap<Reverse<usize>> = BinaryHeap::new();
    for (i, value) in indegree.iter().enumerate() {
        if *value == 0 {
            ready.push(Reverse(i));
        }
    }
    let mut order = Vec::with_capacity(n);
    while let Some(Reverse(node)) = ready.pop() {
        order.push(node);
        for child in &children[node] {
            indegree[*child] -= 1;
            if indegree[*child] == 0 {
                ready.push(Reverse(*child));
            }
        }
    }
    if order.len() != n {
        return Err(
            "Cycle detected in pedigree; cannot compute inbreeding coefficients.".to_string(),
        );
    }

    let mut new_index = vec![0usize; n];
    for (pos, node) in order.iter().enumerate() {
        new_index[*node] = pos + 1;
    }
    let mut ped_sire = vec![0usize; n + 1];
    let mut ped_dam = vec![0usize; n + 1];
    for pos in 1..=n {
        let node = order[pos - 1];
        ped_sire[pos] = sire_idx[node].map(|idx| new_index[idx]).unwrap_or(0);
        ped_dam[pos] = dam_idx[node].map(|idx| new_index[idx]).unwrap_or(0);
    }

    let mut sid = vec![0usize; n + 1];
    let mut link = vec![0usize; n + 1];
    let mut max_idp = vec![0usize; n + 1];
    let mut f = vec![0.0f64; n + 1];
    let mut b = vec![0.0f64; n + 1];
    let mut x = vec![0.0f64; n + 1];
    let mut rped_s = vec![0usize; n + 1];
    let mut rped_d = vec![0usize; n + 1];
    f[0] = -1.0;

    let mut rn = 1usize;
    for i in 1..=n {
        sid[i] = i;
        let s = ped_sire[i];
        let d = ped_dam[i];
        if s != 0 && link[s] == 0 {
            max_idp[rn] = rn;
            link[s] = rn;
            rped_s[rn] = link[ped_sire[s]];
            rped_d[rn] = link[ped_dam[s]];
            rn += 1;
        }
        if d != 0 && link[d] == 0 {
            link[d] = rn;
            rped_s[rn] = link[ped_sire[d]];
            rped_d[rn] = link[ped_dam[d]];
            rn += 1;
        }
        if max_idp[link[s]] < link[d] {
            max_idp[link[s]] = link[d];
        }
    }

    let mut sorted_ids: Vec<usize> = (1..=n).collect();
    sorted_ids.sort_by_key(|idx| ped_sire[*idx]);
    for i in 1..=n {
        sid[i] = sorted_ids[i - 1];
    }

    let mut k = 1usize;
    let mut i = 1usize;
    while i <= n {
        if ped_sire[sid[i]] == 0 {
            f[sid[i]] = 0.0;
            i += 1;
            continue;
        }
        let s = ped_sire[sid[i]];
        let rs = link[s];
        if rs == 0 {
            f[sid[i]] = 0.0;
            i += 1;
            continue;
        }
        let mip = max_idp[rs];
        x[rs] = 1.0;
        while k <= s {
            if link[k] != 0 {
                b[link[k]] = 0.5 - 0.25 * (f[ped_sire[k]] + f[ped_dam[k]]);
            }
            k += 1;
        }
        for j in (1..=rs).rev() {
            if x[j] != 0.0 {
                if rped_s[j] != 0 {
                    x[rped_s[j]] += x[j] * 0.5;
                }
                if rped_d[j] != 0 {
                    x[rped_d[j]] += x[j] * 0.5;
                }
                x[j] *= b[j];
            }
        }
        for j in 1..=mip {
            x[j] += (x[rped_s[j]] + x[rped_d[j]]) * 0.5;
        }
        while i <= n {
            if s != ped_sire[sid[i]] {
                break;
            }
            let dam = ped_dam[sid[i]];
            f[sid[i]] = x[link[dam]] * 0.5;
            i += 1;
        }
        for j in 1..=mip {
            x[j] = 0.0;
        }
    }

    let mut result = vec![0.0f64; n];
    for idx in 0..n {
        result[idx] = f[new_index[idx]];
    }
    Ok(result)
}

fn row_completeness(values: &[&String]) -> usize {
    values.iter().filter(|value| !is_missing(value)).count()
}

fn detect_loops_for_fix(ids: &[String], sires: &[String], dams: &[String]) -> Vec<Vec<String>> {
    let id_set: HashSet<String> = ids.iter().cloned().collect();
    detect_loops(ids, sires, dams, &id_set)
}

fn push_dict(py: Python<'_>, list: &Bound<'_, PyList>, pairs: &[(&str, String)]) -> PyResult<()> {
    let row = PyDict::new(py);
    for (key, value) in pairs {
        row.set_item(*key, value)?;
    }
    list.append(row)?;
    Ok(())
}

fn break_cycles_for_fix(
    ids: &[String],
    sires: &mut [String],
    dams: &mut [String],
) -> Vec<(String, String, String, Vec<String>)> {
    let mut breaks = Vec::new();
    let id_to_index: HashMap<String, usize> = ids
        .iter()
        .enumerate()
        .map(|(index, id)| (id.clone(), index))
        .collect();
    for _attempt in 0..ids.len().saturating_mul(2).max(1) {
        let cycles = detect_loops_for_fix(ids, sires, dams);
        if cycles.is_empty() {
            break;
        }
        let mut changed = false;
        for cycle in cycles {
            if cycle.len() < 3 {
                continue;
            }
            let child = cycle[cycle.len() - 2].clone();
            let parent = cycle[cycle.len() - 1].clone();
            if let Some(index) = id_to_index.get(&child).copied() {
                if sires[index] == parent {
                    sires[index] = "0".to_string();
                    breaks.push((child, parent, "Sire".to_string(), cycle));
                    changed = true;
                } else if dams[index] == parent {
                    dams[index] = "0".to_string();
                    breaks.push((child, parent, "Dam".to_string(), cycle));
                    changed = true;
                }
            }
        }
        if !changed {
            break;
        }
    }
    breaks
}

#[pyfunction]
#[pyo3(signature = (ids, sires, dams, groups=None, sex=None, birthdates=None))]
#[allow(clippy::too_many_arguments)]
fn auto_fix_pedigree(
    py: Python<'_>,
    ids: Vec<String>,
    sires: Vec<String>,
    dams: Vec<String>,
    groups: Option<Vec<String>>,
    sex: Option<Vec<String>>,
    birthdates: Option<Vec<String>>,
) -> PyResult<PyObject> {
    let n = ids.len();
    if sires.len() != n || dams.len() != n {
        return Err(PyValueError::new_err(
            "ids, sires, and dams must have the same length.",
        ));
    }
    if groups.as_ref().map_or(false, |values| values.len() != n)
        || sex.as_ref().map_or(false, |values| values.len() != n)
        || birthdates
            .as_ref()
            .map_or(false, |values| values.len() != n)
    {
        return Err(PyValueError::new_err(
            "optional columns must have the same length as ids.",
        ));
    }

    let mut clean_ids = Vec::with_capacity(n);
    let mut clean_sires = Vec::with_capacity(n);
    let mut clean_dams = Vec::with_capacity(n);
    let mut clean_groups = Vec::with_capacity(n);
    let mut clean_sex = Vec::with_capacity(n);
    let mut clean_birthdates = Vec::with_capacity(n);
    let missing_id_rows = PyList::empty(py);

    for i in 0..n {
        let id = norm(&ids[i]);
        if is_missing(&id) {
            let row = PyDict::new(py);
            row.set_item("row", i + 1)?;
            missing_id_rows.append(row)?;
            continue;
        }
        clean_ids.push(id);
        clean_sires.push(normalize_parent(&sires[i]));
        clean_dams.push(normalize_parent(&dams[i]));
        clean_groups.push(
            groups
                .as_ref()
                .and_then(|values| values.get(i))
                .map(|v| norm(v))
                .unwrap_or_default(),
        );
        clean_sex.push(
            sex.as_ref()
                .and_then(|values| values.get(i))
                .map(|v| norm(v))
                .unwrap_or_default(),
        );
        clean_birthdates.push(
            birthdates
                .as_ref()
                .and_then(|values| values.get(i))
                .map(|v| norm(v))
                .unwrap_or_default(),
        );
    }

    let mut best_by_id: HashMap<String, (usize, usize)> = HashMap::new();
    let mut id_counts: HashMap<String, usize> = HashMap::new();
    for i in 0..clean_ids.len() {
        *id_counts.entry(clean_ids[i].clone()).or_insert(0) += 1;
        let score = row_completeness(&[
            &clean_ids[i],
            &clean_sires[i],
            &clean_dams[i],
            &clean_groups[i],
            &clean_sex[i],
            &clean_birthdates[i],
        ]);
        match best_by_id.get(&clean_ids[i]).copied() {
            Some((_best_index, best_score)) if best_score >= score => {}
            _ => {
                best_by_id.insert(clean_ids[i].clone(), (i, score));
            }
        }
    }
    let duplicate_records = PyList::empty(py);
    let kept_duplicate_records = PyList::empty(py);
    let mut duplicate_ids: Vec<String> = id_counts
        .iter()
        .filter(|(_id, count)| **count > 1)
        .map(|(id, _count)| id.clone())
        .collect();
    duplicate_ids.sort();
    let duplicate_id_set: HashSet<String> = duplicate_ids.iter().cloned().collect();
    let mut keep = vec![false; clean_ids.len()];
    for id in &duplicate_ids {
        if let Some((kept, _score)) = best_by_id.get(id).copied() {
            keep[kept] = true;
            push_dict(
                py,
                &kept_duplicate_records,
                &[("id", id.clone()), ("row", (kept + 1).to_string())],
            )?;
        }
    }
    for (id, (index, _score)) in &best_by_id {
        if !duplicate_id_set.contains(id) {
            keep[*index] = true;
        }
    }
    for i in 0..clean_ids.len() {
        if duplicate_id_set.contains(&clean_ids[i]) && !keep[i] {
            push_dict(
                py,
                &duplicate_records,
                &[("id", clean_ids[i].clone()), ("row", (i + 1).to_string())],
            )?;
        }
    }

    let mut ids_fixed = Vec::new();
    let mut sires_fixed = Vec::new();
    let mut dams_fixed = Vec::new();
    let mut groups_fixed = Vec::new();
    let mut sex_fixed = Vec::new();
    let mut birthdates_fixed = Vec::new();
    for i in 0..clean_ids.len() {
        if keep[i] {
            ids_fixed.push(clean_ids[i].clone());
            sires_fixed.push(clean_sires[i].clone());
            dams_fixed.push(clean_dams[i].clone());
            groups_fixed.push(clean_groups[i].clone());
            sex_fixed.push(clean_sex[i].clone());
            birthdates_fixed.push(clean_birthdates[i].clone());
        }
    }

    let self_parent_records = PyList::empty(py);
    for i in 0..ids_fixed.len() {
        if sires_fixed[i] == ids_fixed[i] {
            push_dict(py, &self_parent_records, &[("id", ids_fixed[i].clone()), ("field", "Sire".to_string())])?;
            sires_fixed[i] = "0".to_string();
        }
        if dams_fixed[i] == ids_fixed[i] {
            push_dict(py, &self_parent_records, &[("id", ids_fixed[i].clone()), ("field", "Dam".to_string())])?;
            dams_fixed[i] = "0".to_string();
        }
    }

    let mut id_set: HashSet<String> = ids_fixed.iter().cloned().collect();
    let mut missing_parents: HashSet<String> = HashSet::new();
    for i in 0..ids_fixed.len() {
        for parent in [&sires_fixed[i], &dams_fixed[i]] {
            if parent != "0" && !id_set.contains(parent) {
                missing_parents.insert(parent.clone());
            }
        }
    }
    let mut missing_parent_ids: Vec<String> = missing_parents.into_iter().collect();
    missing_parent_ids.sort();
    for parent in &missing_parent_ids {
        ids_fixed.push(parent.clone());
        sires_fixed.push("0".to_string());
        dams_fixed.push("0".to_string());
        groups_fixed.push(String::new());
        sex_fixed.push(String::new());
        birthdates_fixed.push(String::new());
        id_set.insert(parent.clone());
    }

    let birthdate_records = PyList::empty(py);
    if birthdates.is_some() {
        let mut birth_map: HashMap<String, i64> = HashMap::new();
        for i in 0..ids_fixed.len() {
            if let Some(value) = parse_birthdate(&birthdates_fixed[i]) {
                birth_map.insert(ids_fixed[i].clone(), value);
            }
        }
        let mut invalid: HashSet<String> = HashSet::new();
        for i in 0..ids_fixed.len() {
            if let Some(child_date) = birth_map.get(&ids_fixed[i]) {
                for parent in [&sires_fixed[i], &dams_fixed[i]] {
                    if let Some(parent_date) = birth_map.get(parent) {
                        if parent_date >= child_date {
                            invalid.insert(ids_fixed[i].clone());
                        }
                    }
                }
            }
        }
        let mut invalid_vec: Vec<String> = invalid.into_iter().collect();
        invalid_vec.sort();
        for item_id in invalid_vec {
            if let Some(index) = ids_fixed.iter().position(|value| *value == item_id) {
                birthdates_fixed[index] = "0".to_string();
                push_dict(py, &birthdate_records, &[("id", item_id), ("field", "BirthDate".to_string())])?;
            }
        }
    }

    let loop_breaks = PyList::empty(py);
    let broken = break_cycles_for_fix(&ids_fixed, &mut sires_fixed, &mut dams_fixed);
    for (child, parent, field, cycle) in &broken {
        let row = PyDict::new(py);
        row.set_item("child", child)?;
        row.set_item("parent", parent)?;
        row.set_item("field", field)?;
        row.set_item("cycle", PyList::new(py, cycle)?)?;
        loop_breaks.append(row)?;
    }

    let missing_ids_count = missing_id_rows.len();
    let duplicates_count = duplicate_records.len();
    let missing_parents_count = missing_parent_ids.len();
    let self_parent_count = self_parent_records.len();
    let birthdate_count = birthdate_records.len();
    let loops_count = loop_breaks.len();
    let total_actions = missing_ids_count
        + duplicates_count
        + missing_parents_count
        + self_parent_count
        + birthdate_count
        + loops_count;

    let autofix = PyDict::new(py);
    autofix.set_item("missing_ids", missing_ids_count)?;
    autofix.set_item("duplicates", duplicates_count)?;
    autofix.set_item("missing_parents", missing_parents_count)?;
    autofix.set_item("self_parent", self_parent_count)?;
    autofix.set_item("birthdate", birthdate_count)?;
    autofix.set_item("loops", loops_count)?;
    autofix.set_item("missing_id_rows", missing_id_rows)?;
    autofix.set_item("duplicate_records", duplicate_records)?;
    autofix.set_item("kept_duplicate_records", kept_duplicate_records)?;
    autofix.set_item("missing_parent_ids", PyList::new(py, &missing_parent_ids)?)?;
    autofix.set_item("self_parent_records", self_parent_records)?;
    autofix.set_item("birthdate_records", birthdate_records)?;
    autofix.set_item("loop_breaks", loop_breaks)?;
    autofix.set_item("total_actions", total_actions)?;

    let result = PyDict::new(py);
    result.set_item("ids", PyList::new(py, &ids_fixed)?)?;
    result.set_item("sires", PyList::new(py, &sires_fixed)?)?;
    result.set_item("dams", PyList::new(py, &dams_fixed)?)?;
    result.set_item("groups", PyList::new(py, &groups_fixed)?)?;
    result.set_item("sex", PyList::new(py, &sex_fixed)?)?;
    result.set_item("birthdates", PyList::new(py, &birthdates_fixed)?)?;
    result.set_item("autofix", autofix)?;
    Ok(result.into_any().unbind())
}

#[pyfunction]
#[pyo3(signature = (ids, sires, dams, groups=None, sex=None, birthdates=None))]
#[allow(clippy::too_many_arguments)]
fn analyze_pedigree(
    py: Python<'_>,
    ids: Vec<String>,
    sires: Vec<String>,
    dams: Vec<String>,
    groups: Option<Vec<String>>,
    sex: Option<Vec<String>>,
    birthdates: Option<Vec<String>>,
) -> PyResult<PyObject> {
    let n = ids.len();
    if sires.len() != n || dams.len() != n {
        return Err(PyValueError::new_err(
            "ids, sires, and dams must have the same length.",
        ));
    }
    if groups.as_ref().map_or(false, |values| values.len() != n)
        || sex.as_ref().map_or(false, |values| values.len() != n)
        || birthdates
            .as_ref()
            .map_or(false, |values| values.len() != n)
    {
        return Err(PyValueError::new_err(
            "optional columns must have the same length as ids.",
        ));
    }

    let mut clean_ids = Vec::with_capacity(n);
    let mut clean_sires = Vec::with_capacity(n);
    let mut clean_dams = Vec::with_capacity(n);
    let mut clean_groups = Vec::with_capacity(n);
    let mut clean_sex = Vec::with_capacity(n);
    let mut clean_birthdates = Vec::with_capacity(n);
    let mut missing_progeny = Vec::new();
    for i in 0..n {
        let id = norm(&ids[i]);
        if is_missing(&id) {
            missing_progeny.push(id);
            continue;
        }
        clean_ids.push(id);
        clean_sires.push(normalize_parent(&sires[i]));
        clean_dams.push(normalize_parent(&dams[i]));
        clean_groups.push(
            groups
                .as_ref()
                .and_then(|values| values.get(i))
                .map(|v| norm(v))
                .unwrap_or_default(),
        );
        clean_sex.push(
            sex.as_ref()
                .and_then(|values| values.get(i))
                .map(|v| norm(v))
                .unwrap_or_default(),
        );
        clean_birthdates.push(
            birthdates
                .as_ref()
                .and_then(|values| values.get(i))
                .map(|v| norm(v))
                .unwrap_or_default(),
        );
    }
    let n = clean_ids.len();

    let mut id_set = HashSet::with_capacity(n * 2);
    let mut id_count: HashMap<String, usize> = HashMap::with_capacity(n * 2);
    let mut duplicate_ids = Vec::new();
    for id in &clean_ids {
        id_set.insert(id.clone());
        let counter = id_count.entry(id.clone()).or_insert(0);
        *counter += 1;
        if *counter == 2 {
            duplicate_ids.push(id.clone());
        }
    }

    let mut missing_sires = HashSet::new();
    let mut missing_dams = HashSet::new();
    let mut sires_mentioned = HashSet::new();
    let mut dams_mentioned = HashSet::new();
    let mut self_parent_ids = Vec::new();
    let mut founders = 0usize;
    let mut with_both = 0usize;
    let mut only_sire = 0usize;
    let mut only_dam = 0usize;
    let mut sire_progeny_count: HashMap<String, usize> = HashMap::new();
    let mut dam_progeny_count: HashMap<String, usize> = HashMap::new();

    for i in 0..n {
        let has_sire = clean_sires[i] != "0";
        let has_dam = clean_dams[i] != "0";
        if !has_sire && !has_dam {
            founders += 1;
        } else if has_sire && has_dam {
            with_both += 1;
        } else if has_sire {
            only_sire += 1;
        } else {
            only_dam += 1;
        }
        if (has_sire && clean_sires[i] == clean_ids[i])
            || (has_dam && clean_dams[i] == clean_ids[i])
        {
            self_parent_ids.push(clean_ids[i].clone());
        }
        if has_sire {
            sires_mentioned.insert(clean_sires[i].clone());
            *sire_progeny_count
                .entry(clean_sires[i].clone())
                .or_insert(0) += 1;
            if !id_set.contains(&clean_sires[i]) {
                missing_sires.insert(clean_sires[i].clone());
            }
        }
        if has_dam {
            dams_mentioned.insert(clean_dams[i].clone());
            *dam_progeny_count.entry(clean_dams[i].clone()).or_insert(0) += 1;
            if !id_set.contains(&clean_dams[i]) {
                missing_dams.insert(clean_dams[i].clone());
            }
        }
    }

    let mut dual_role_ids: Vec<String> = sires_mentioned
        .intersection(&dams_mentioned)
        .cloned()
        .collect();
    dual_role_ids.sort();
    let mut missing_sires_vec: Vec<String> = missing_sires.into_iter().collect();
    missing_sires_vec.sort();
    let mut missing_dams_vec: Vec<String> = missing_dams.into_iter().collect();
    missing_dams_vec.sort();

    let mut sex_map = HashMap::new();
    for i in 0..n {
        if let Some(code) = sex_code(&clean_sex[i]) {
            sex_map.insert(clean_ids[i].clone(), code);
        }
    }
    let mut sex_mismatch_sire_ids = Vec::new();
    let mut sex_mismatch_dam_ids = Vec::new();
    if !sex_map.is_empty() {
        for i in 0..n {
            if clean_sires[i] != "0"
                && sex_map
                    .get(&clean_sires[i])
                    .is_some_and(|code| *code != 'M')
            {
                sex_mismatch_sire_ids.push(clean_sires[i].clone());
            }
            if clean_dams[i] != "0" && sex_map.get(&clean_dams[i]).is_some_and(|code| *code != 'F')
            {
                sex_mismatch_dam_ids.push(clean_dams[i].clone());
            }
        }
        sex_mismatch_sire_ids.sort();
        sex_mismatch_sire_ids.dedup();
        sex_mismatch_dam_ids.sort();
        sex_mismatch_dam_ids.dedup();
    }

    let mut birth_map = HashMap::new();
    for i in 0..n {
        if let Some(value) = parse_birthdate(&clean_birthdates[i]) {
            birth_map.insert(clean_ids[i].clone(), value);
        }
    }
    let mut birthdate_invalid_offspring_ids = Vec::new();
    let mut birthdate_invalid_sire_ids = Vec::new();
    let mut birthdate_invalid_dam_ids = Vec::new();
    if !birth_map.is_empty() {
        for i in 0..n {
            if let Some(child_date) = birth_map.get(&clean_ids[i]) {
                if clean_sires[i] != "0" {
                    if let Some(parent_date) = birth_map.get(&clean_sires[i]) {
                        if parent_date >= child_date {
                            birthdate_invalid_offspring_ids.push(clean_ids[i].clone());
                            birthdate_invalid_sire_ids.push(clean_sires[i].clone());
                        }
                    }
                }
                if clean_dams[i] != "0" {
                    if let Some(parent_date) = birth_map.get(&clean_dams[i]) {
                        if parent_date >= child_date {
                            birthdate_invalid_offspring_ids.push(clean_ids[i].clone());
                            birthdate_invalid_dam_ids.push(clean_dams[i].clone());
                        }
                    }
                }
            }
        }
        birthdate_invalid_offspring_ids.sort();
        birthdate_invalid_offspring_ids.dedup();
        birthdate_invalid_sire_ids.sort();
        birthdate_invalid_sire_ids.dedup();
        birthdate_invalid_dam_ids.sort();
        birthdate_invalid_dam_ids.dedup();
    }

    let loops = py.allow_threads(|| detect_loops(&clean_ids, &clean_sires, &clean_dams, &id_set));
    let f_values = if duplicate_ids.is_empty() && loops.is_empty() {
        py.allow_threads(|| inbreeding(&clean_ids, &clean_sires, &clean_dams))
            .unwrap_or_else(|_| vec![f64::NAN; n])
    } else {
        vec![f64::NAN; n]
    };
    let finite_f: Vec<f64> = f_values.iter().copied().filter(|v| v.is_finite()).collect();
    let inbred_f: Vec<f64> = finite_f.iter().copied().filter(|v| *v > 0.0).collect();
    let non_founders = n.saturating_sub(founders);
    let parent_ids_with_progeny: HashSet<String> =
        sires_mentioned.union(&dams_mentioned).cloned().collect();
    let individuals_with_progeny = parent_ids_with_progeny
        .iter()
        .filter(|id| id_set.contains(*id))
        .count();
    let individuals_without_progeny = n.saturating_sub(individuals_with_progeny);

    let founder_ids: HashSet<String> = (0..n)
        .filter(|index| clean_sires[*index] == "0" && clean_dams[*index] == "0")
        .map(|index| clean_ids[index].clone())
        .collect();
    let founder_parent_ids: HashSet<String> = parent_ids_with_progeny
        .intersection(&founder_ids)
        .cloned()
        .collect();
    let founder_sire_ids: HashSet<String> = sires_mentioned
        .intersection(&founder_ids)
        .cloned()
        .collect();
    let founder_dam_ids: HashSet<String> =
        dams_mentioned.intersection(&founder_ids).cloned().collect();
    let founder_progeny = founder_parent_ids
        .iter()
        .map(|id| {
            sire_progeny_count.get(id).copied().unwrap_or(0)
                + dam_progeny_count.get(id).copied().unwrap_or(0)
        })
        .sum::<usize>();
    let founder_sire_progeny = founder_sire_ids
        .iter()
        .map(|id| sire_progeny_count.get(id).copied().unwrap_or(0))
        .sum::<usize>();
    let founder_dam_progeny = founder_dam_ids
        .iter()
        .map(|id| dam_progeny_count.get(id).copied().unwrap_or(0))
        .sum::<usize>();

    let non_founder_ids: HashSet<String> = id_set.difference(&founder_ids).cloned().collect();
    let non_founder_sire_ids: HashSet<String> = sires_mentioned
        .intersection(&non_founder_ids)
        .cloned()
        .collect();
    let non_founder_dam_ids: HashSet<String> = dams_mentioned
        .intersection(&non_founder_ids)
        .cloned()
        .collect();
    let non_founder_sire_progeny = non_founder_sire_ids
        .iter()
        .map(|id| sire_progeny_count.get(id).copied().unwrap_or(0))
        .sum::<usize>();
    let non_founder_dam_progeny = non_founder_dam_ids
        .iter()
        .map(|id| dam_progeny_count.get(id).copied().unwrap_or(0))
        .sum::<usize>();

    let mut full_sib_counts: HashMap<(String, String), usize> = HashMap::new();
    for i in 0..n {
        if clean_sires[i] != "0" && clean_dams[i] != "0" {
            *full_sib_counts
                .entry((clean_sires[i].clone(), clean_dams[i].clone()))
                .or_insert(0) += 1;
        }
    }
    let full_sib_sizes: Vec<usize> = full_sib_counts
        .values()
        .copied()
        .filter(|size| *size >= 2)
        .collect();
    let full_sib_groups = full_sib_sizes.len();
    let full_sib_average = if full_sib_groups > 0 {
        full_sib_sizes.iter().sum::<usize>() as f64 / full_sib_groups as f64
    } else {
        0.0
    };
    let full_sib_max = full_sib_sizes.iter().copied().max().unwrap_or(0);
    let full_sib_min = full_sib_sizes.iter().copied().min().unwrap_or(0);

    let lap_depths =
        py.allow_threads(|| longest_ancestral_path(&clean_ids, &clean_sires, &clean_dams, &id_set));
    let lap_mean = if lap_depths.is_empty() {
        0.0
    } else {
        lap_depths.iter().sum::<usize>() as f64 / lap_depths.len() as f64
    };
    let mut lap_counts: HashMap<usize, usize> = HashMap::new();
    for depth in &lap_depths {
        *lap_counts.entry(*depth).or_insert(0) += 1;
    }

    let meta = PyDict::new(py);
    meta.set_item("total", n)?;
    meta.set_item("founders", founders)?;
    meta.set_item("non_founders", non_founders)?;
    meta.set_item("with_both_parents", with_both)?;
    meta.set_item("only_sire", only_sire)?;
    meta.set_item("only_dam", only_dam)?;
    meta.set_item("duplicate_count", duplicate_ids.len())?;
    meta.set_item("missing_sires_count", missing_sires_vec.len())?;
    meta.set_item("missing_dams_count", missing_dams_vec.len())?;
    meta.set_item("self_parent_count", self_parent_ids.len())?;
    meta.set_item("dual_role_count", dual_role_ids.len())?;
    meta.set_item("loop_count", loops.len())?;
    meta.set_item("checked_sex", !sex_map.is_empty())?;
    meta.set_item("checked_birthdate", !birth_map.is_empty())?;
    meta.set_item("missing_progeny_count", missing_progeny.len())?;

    let parent_stats = PyDict::new(py);
    parent_stats.set_item("sires_total", sires_mentioned.len())?;
    parent_stats.set_item(
        "sire_progeny",
        clean_sires.iter().filter(|value| *value != "0").count(),
    )?;
    parent_stats.set_item("dams_total", dams_mentioned.len())?;
    parent_stats.set_item(
        "dam_progeny",
        clean_dams.iter().filter(|value| *value != "0").count(),
    )?;
    parent_stats.set_item("individuals_with_progeny", individuals_with_progeny)?;
    parent_stats.set_item("individuals_without_progeny", individuals_without_progeny)?;

    let founder_stats = PyDict::new(py);
    founder_stats.set_item("founders", founders)?;
    founder_stats.set_item("progeny", founder_progeny)?;
    founder_stats.set_item("sires", founder_sire_ids.len())?;
    founder_stats.set_item("sire_progeny", founder_sire_progeny)?;
    founder_stats.set_item("dams", founder_dam_ids.len())?;
    founder_stats.set_item("dam_progeny", founder_dam_progeny)?;
    founder_stats.set_item(
        "with_no_progeny",
        founders.saturating_sub(founder_parent_ids.len()),
    )?;

    let non_founder_stats = PyDict::new(py);
    non_founder_stats.set_item("non_founders", non_founders)?;
    non_founder_stats.set_item("sires", non_founder_sire_ids.len())?;
    non_founder_stats.set_item("sire_progeny", non_founder_sire_progeny)?;
    non_founder_stats.set_item("dams", non_founder_dam_ids.len())?;
    non_founder_stats.set_item("dam_progeny", non_founder_dam_progeny)?;
    non_founder_stats.set_item("only_sire", only_sire)?;
    non_founder_stats.set_item("only_dam", only_dam)?;
    non_founder_stats.set_item("with_both_parents", with_both)?;

    let full_sib = PyDict::new(py);
    full_sib.set_item("groups", full_sib_groups)?;
    full_sib.set_item("average_family_size", full_sib_average)?;
    full_sib.set_item("maximum", full_sib_max)?;
    full_sib.set_item("minimum", full_sib_min)?;

    let lap = PyDict::new(py);
    lap.set_item("mean_generation_depth", lap_mean)?;
    let lap_distribution = PyList::empty(py);
    let mut lap_keys: Vec<usize> = lap_counts.keys().copied().collect();
    lap_keys.sort_unstable();
    for depth in lap_keys {
        let row = PyDict::new(py);
        row.set_item("depth", depth)?;
        row.set_item("count", lap_counts[&depth])?;
        lap_distribution.append(row)?;
    }
    lap.set_item("distribution", lap_distribution)?;

    let errors = PyDict::new(py);
    errors.set_item("duplicate_ids", py_string_list(py, &duplicate_ids)?)?;
    errors.set_item("missing_sires", py_string_list(py, &missing_sires_vec)?)?;
    errors.set_item("missing_dams", py_string_list(py, &missing_dams_vec)?)?;
    errors.set_item("dual_role_ids", py_string_list(py, &dual_role_ids)?)?;
    errors.set_item("self_parent_ids", py_string_list(py, &self_parent_ids)?)?;
    errors.set_item("missing_progeny_ids", py_string_list(py, &missing_progeny)?)?;
    errors.set_item(
        "sex_mismatch_sire_ids",
        py_string_list(py, &sex_mismatch_sire_ids)?,
    )?;
    errors.set_item(
        "sex_mismatch_dam_ids",
        py_string_list(py, &sex_mismatch_dam_ids)?,
    )?;
    errors.set_item(
        "birthdate_invalid_offspring_ids",
        py_string_list(py, &birthdate_invalid_offspring_ids)?,
    )?;
    errors.set_item(
        "birthdate_invalid_sire_ids",
        py_string_list(py, &birthdate_invalid_sire_ids)?,
    )?;
    errors.set_item(
        "birthdate_invalid_dam_ids",
        py_string_list(py, &birthdate_invalid_dam_ids)?,
    )?;
    let loop_list = PyList::empty(py);
    for cycle in &loops {
        loop_list.append(PyList::new(py, cycle)?)?;
    }
    errors.set_item("loop_cycles", loop_list)?;

    let records = PyList::empty(py);
    for i in 0..n {
        let row = PyDict::new(py);
        row.set_item("id", &clean_ids[i])?;
        row.set_item("sire", &clean_sires[i])?;
        row.set_item("dam", &clean_dams[i])?;
        row.set_item("group", &clean_groups[i])?;
        row.set_item("sex", &clean_sex[i])?;
        row.set_item("birthdate", &clean_birthdates[i])?;
        row.set_item("lap_depth", lap_depths.get(i).copied().unwrap_or(0))?;
        row.set_item("inbreeding", f_values[i])?;
        records.append(row)?;
    }

    let distribution = PyList::empty(py);
    let zero_count = finite_f.iter().filter(|v| **v == 0.0).count();
    let zero_row = PyDict::new(py);
    zero_row.set_item("range", "F = 0")?;
    zero_row.set_item("count", zero_count)?;
    distribution.append(zero_row)?;
    for step in 0..20 {
        let low = step as f64 * 0.05;
        let high = (step + 1) as f64 * 0.05;
        let label = format!("{low:.2} < F <= {high:.2}");
        let count = finite_f.iter().filter(|v| **v > low && **v <= high).count();
        let row = PyDict::new(py);
        row.set_item("range", label)?;
        row.set_item("count", count)?;
        distribution.append(row)?;
    }

    let mut top_indices: Vec<usize> = (0..n).collect();
    top_indices.sort_by(|a, b| {
        f_values[*b]
            .partial_cmp(&f_values[*a])
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    let top = PyList::empty(py);
    for idx in top_indices.into_iter().take(20) {
        if !f_values[idx].is_finite() {
            continue;
        }
        let row = PyDict::new(py);
        row.set_item("id", &clean_ids[idx])?;
        row.set_item("sire", &clean_sires[idx])?;
        row.set_item("dam", &clean_dams[idx])?;
        row.set_item("group", &clean_groups[idx])?;
        row.set_item("sex", &clean_sex[idx])?;
        row.set_item("birthdate", &clean_birthdates[idx])?;
        row.set_item("inbreeding", f_values[idx])?;
        top.append(row)?;
    }

    let mut group_map: HashMap<String, Vec<f64>> = HashMap::new();
    for i in 0..n {
        if clean_groups[i].is_empty() || !f_values[i].is_finite() {
            continue;
        }
        group_map
            .entry(clean_groups[i].clone())
            .or_default()
            .push(f_values[i]);
    }
    let group_summary = PyList::empty(py);
    let mut group_names: Vec<String> = group_map.keys().cloned().collect();
    group_names.sort();
    for group in group_names {
        let values = &group_map[&group];
        let (_, _min, max, mean, _sd) = stats(values);
        let row = PyDict::new(py);
        row.set_item("group", group)?;
        row.set_item("total", values.len())?;
        row.set_item("mean", mean)?;
        row.set_item("max", max)?;
        row.set_item("inbred_count", values.iter().filter(|v| **v > 0.0).count())?;
        row.set_item("f_ge_0_125", values.iter().filter(|v| **v >= 0.125).count())?;
        row.set_item("f_ge_0_25", values.iter().filter(|v| **v >= 0.25).count())?;
        group_summary.append(row)?;
    }

    let inbreeding_dict = PyDict::new(py);
    inbreeding_dict.set_item("records", records)?;
    inbreeding_dict.set_item("stats_all", set_stats(py, &finite_f)?)?;
    inbreeding_dict.set_item("stats_inbred", set_stats(py, &inbred_f)?)?;
    inbreeding_dict.set_item("distribution", distribution)?;
    inbreeding_dict.set_item("top_high", top)?;

    let result = PyDict::new(py);
    result.set_item("meta", meta)?;
    result.set_item("parent_stats", parent_stats)?;
    result.set_item("founder_stats", founder_stats)?;
    result.set_item("non_founder_stats", non_founder_stats)?;
    result.set_item("full_sib", full_sib)?;
    result.set_item("lap", lap)?;
    result.set_item("errors", errors)?;
    result.set_item("inbreeding", inbreeding_dict)?;
    result.set_item("group_summary", group_summary)?;
    Ok(result.into_any().unbind())
}

#[pymodule]
fn writeonside_pedigree(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(analyze_pedigree, module)?)?;
    module.add_function(wrap_pyfunction!(auto_fix_pedigree, module)?)?;
    Ok(())
}
