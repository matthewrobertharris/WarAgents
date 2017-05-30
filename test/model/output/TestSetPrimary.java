package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.output.Action.Activity;
import model.position.Current;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestSetPrimary extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	@Test
	public void testSetPrimary_Success() {
		String file = "resources\\test\\outputMaps\\test_setPrimary_success.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		int x = 0;
		int y = 0;
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.SET_PRIMARY);
		assertTrue(map.getAllAgents().size() == numAgents);
		assertTrue(agent.getPrimary().getX() == x);
		assertTrue(agent.getPrimary().getY() == y);
	}
	
	@Test
	public void test_ToString() {
		Current position = new Current();
		SetPrimary output = new SetPrimary(position);
		String strOutput = "SET_PRIMARY";
		assertTrue(output.toString().equals(strOutput));
	}
}
