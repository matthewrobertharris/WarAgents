package model.tree;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Set;

public class Tree {

	private String name;
	private Node root;
	private HashMap<Integer, Integer> heights;

	public Tree(String name) {
		setName(name);
		setRoot(null);
		setHeights(new HashMap<Integer, Integer>());
		setHeights();
	}

	public Tree(String name, Node root) {
		setName(name);
		setRoot(root);
		setHeights(new HashMap<Integer, Integer>());
		setHeights();
	}

	public String getName() {
		return name;
	}

	public HashMap<Integer, Integer> getHeights() {
		return heights;
	}

	public void setHeights(HashMap<Integer, Integer> heights) {
		this.heights = heights;
	}

	public void setHeights() {
		recursiveHeights(getRoot());
	}

	private void recursiveHeights(Node node) {
		if (node != null) {
			int level = node.getHeight();
			int total = 1;
			if (getHeights().containsKey(level)) {
				total += getHeights().get(level);
			}
			getHeights().put(level, total);
			for (Node child : node.getChildren()) {
				recursiveHeights(child);
			}
		}
	}

	public void setName(String name) {
		this.name = name;
	}

	public Node getRoot() {
		return root;
	}

	public void setRoot(Node root) {
		this.root = root;
	}

	public int getNumberNodes(int height) {
		return getHeights().get(height);
	}

	public int getMaxHeight() {
		return getHeights().keySet().size();
	}

	public String toString() {
		String output = "name=" + getName();
		Set<Integer> keys = getHeights().keySet();
		Iterator<Integer> itr = keys.iterator();
		while(itr.hasNext()) {
			Integer key = itr.next();
			output += "key=" + key + " value=" + getHeights().get(key);
		}
		output += "\t" + getRoot().toString();
		return output;
	}
}
