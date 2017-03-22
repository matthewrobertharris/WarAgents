package model.tree;

import java.util.ArrayList;
import java.util.List;

import model.input.Input;

public class Node {

	private List<Input> inputs;
	private List<Node> children;
	private Node parent;
	private int type;
	private int height;
	private Tree tree;

	/**
	 * TODO check that child is an instance of Output
	 * 
	 * @param parent
	 * @param child
	 * @throws Exception
	 */
	public Node(Node parent, Tree tree) {
		setInputs(null);
		setChildren(new ArrayList<Node>());
		setParent(parent);
		setType(1);
		if(parent == null) {
			setHeight(0);
		}
		else {
			setHeight(parent.getHeight() + 1);
		}
		setTree(tree);
	}

	/**
	 * TODO Check the type vs children vs inputs sizes to make sure they work
	 * 
	 * @param inputs
	 * @param type
	 * @param children
	 * @param parent
	 */
	public Node(List<Input> inputs, int type, List<Node> children, Node parent, Tree tree) {
		setInputs(inputs);
		setType(type);
		setChildren(children);
		setParent(parent);
		setTree(tree);
		if(parent == null) {
			setHeight(0);
		}
		else {
			setHeight(parent.getHeight() + 1);
		}
		
	}

	public Tree getTree() {
		return tree;
	}

	public void setTree(Tree tree) {
		this.tree = tree;
	}

	public int getHeight() {
		return height;
	}

	public void setHeight(int height) {
		this.height = height;
	}

	public Node getParent() {
		return parent;
	}

	public void setParent(Node parent) {
		this.parent = parent;
	}

	public List<Node> getChildren() {
		return children;
	}

	public void setChildren(List<Node> children) {
		this.children = children;
	}

	public List<Input> getInputs() {
		return inputs;
	}

	public void setInputs(List<Input> inputs) {
		this.inputs = inputs;
	}

	public int getType() {
		return type;
	}

	public void setType(int type) {
		this.type = type;
	}

	public String toString() {
		String output = "(" + getTree().getName() + "|" + convertType();
		for(Input input : getInputs()) {
			output += " " + input.toString();
		}
		for (Node node : getChildren()) {
			output += node.toString();
		}
		output += ")";
		return output;
	}

	private String convertType() {
		switch (getType()) {
		case 1:
			return "OUTPUT";
		case 2:
			return "BOOLEAN";
		case 3:
			return "NUMERIC";
		case 4:
			return "POSITION";
		default:
			return "OUTPUT";
		}
	}

}
